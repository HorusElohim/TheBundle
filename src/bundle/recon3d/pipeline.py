"""Sequential pipeline runner for the Recon3D reconstruction chain."""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import PrivateAttr

from bundle.core import logger
from bundle.core.data import Data
from bundle.core.entity import Entity

from .stages import Stage
from .stages.blender import BlenderStage
from .stages.blender.base import BlenderInput, create_blender_stage
from .stages.gaussians import GaussiansStage, create_gaussians_stage
from .stages.gaussians.base import GaussiansInput, GaussiansOutput
from .stages.sfm import SfmStage, create_sfm_stage
from .stages.sfm.base import SfmBackend, SfmInput, SfmOutput
from .stages.visualization import VisualizationStage, create_visualization_stage
from .stages.visualization.base import VisualizationInput
from .workspace import Workspace

log = logger.get_logger(__name__)


class Pipeline(Entity):
    """Runs a list of stages sequentially, threading each output into the next input.

    After each stage completes, the pipeline writes a ``manifest.json`` into the
    workspace so that ``bundle recon3d status`` can report progress.
    """

    name: str = "recon3d-pipeline"
    workspace: Workspace
    stages: list[Stage] = []
    seed_input: Data | None = None
    """Optional pre-built input for the first stage.

    Set by factories like :meth:`from_gaussians` that skip the usual
    SfM/image bootstrap.  Pydantic validates the value at construction
    time, so callers don't need to reach into private state.
    """

    _last_sfm_output: SfmOutput | None = PrivateAttr(default=None)
    _last_gaussians_output: GaussiansOutput | None = PrivateAttr(default=None)

    model_config = Data.model_config.copy()
    model_config["arbitrary_types_allowed"] = True

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_gaussians(
        cls,
        gaussians_output: GaussiansOutput,
        workspace: Workspace,
        blender: bool = True,
        visualize: bool = False,
    ) -> Pipeline:
        """Create a pipeline that starts from an existing GaussiansOutput.

        Skips SfM and training — useful for synthetic clouds produced by
        ``bundle.gs3d`` or for re-running downstream stages on an existing PLY.

        Args:
            gaussians_output: The reconstructed or synthesised PLY to process.
            workspace: Workspace that provides output directory layout.
            blender: Include the Blender import/render stage.
            visualize: Not supported for synthetic input (requires SfM camera
                poses).  Raises ``NotImplementedError`` if ``True``.
        """
        if visualize:
            raise NotImplementedError(
                "VisualizationStage requires SfM camera poses which are not available "
                "for synthetic Gaussians.  Use blender=True to view in Blender instead."
            )
        if not blender:
            raise ValueError("from_gaussians() needs at least one output stage — pass blender=True.")

        stages: list[Stage] = [create_blender_stage()]
        seed = BlenderInput(
            gaussians_output=gaussians_output,
            blend_output=workspace.root / "blender" / "scene.blend",
        )
        return cls(workspace=workspace, stages=stages, seed_input=seed)

    @classmethod
    def default(
        cls,
        workspace: Workspace,
        sfm_backend: SfmBackend = SfmBackend.COLMAP,
        renderer: str = "3dgut",
        export_usdz: bool = True,
        use_lambda: bool = False,
        lambda_instance_id: str | None = None,
        lambda_auto_terminate: bool = False,
        lambda_filesystem: str | None = None,
        visualize: bool = True,
        vis_backend: str = "opensplat",
        vis_iters: int = 2_000,
        blender: bool = False,
    ) -> Pipeline:
        """Create the standard SfM -> Train -> [Visualize] -> [Blender] pipeline."""
        stages: list[Stage] = [create_sfm_stage(backend=sfm_backend)]

        if use_lambda:
            from .stages.remote.lambda_runner import LambdaRunner

            stages.append(
                LambdaRunner(
                    renderer=renderer if renderer != "auto" else "3dgut",
                    export_usdz=export_usdz,
                    instance_id=lambda_instance_id,
                    auto_terminate=lambda_auto_terminate,
                    filesystem_name=lambda_filesystem,
                )
            )
        else:
            stages.append(create_gaussians_stage(renderer=renderer, export_usdz=export_usdz))

        if visualize:
            stages.append(create_visualization_stage(backend=vis_backend, num_iters=vis_iters))

        if blender:
            stages.append(create_blender_stage())

        return cls(workspace=workspace, stages=stages)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(self) -> dict[str, Data]:
        """Execute all stages in order, returning a map of stage_name -> output."""
        self.workspace.ensure_dirs()
        results: dict[str, Data] = {}
        current_input: Data | None = None

        for i, stage in enumerate(self.stages):
            log.info("Running stage: %s", stage.name)

            if not await stage.check_deps():
                raise RuntimeError(f"Stage '{stage.name}' dependencies not met — run check_deps() for details")

            if current_input is None:
                current_input = self.seed_input if self.seed_input is not None else self._initial_input_for(stage)

            t0 = time.monotonic()
            output = await stage.run(current_input)
            elapsed = time.monotonic() - t0

            log.info("Stage '%s' completed in %.1fs", stage.name, elapsed)
            results[stage.name] = output

            next_stage = self.stages[i + 1] if i + 1 < len(self.stages) else None
            current_input = self._adapt(output, next_stage)

            self._update_manifest(stage.name, elapsed)

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _initial_input_for(self, stage: Stage) -> Data:
        """Build the first input contract from the workspace layout."""
        if isinstance(stage, SfmStage):
            return SfmInput(images_dir=self.workspace.images_dir)
        if isinstance(stage, GaussiansStage):
            raise RuntimeError("GaussiansStage requires SfM output — it cannot be the first stage")
        if isinstance(stage, VisualizationStage):
            raise RuntimeError("VisualizationStage requires GaussiansOutput — it cannot be the first stage")
        if isinstance(stage, BlenderStage):
            raise RuntimeError("BlenderStage requires GaussiansOutput — it cannot be the first stage")
        # LambdaRunner
        raise RuntimeError(f"Unknown stage type as first stage: {type(stage)}")

    def _adapt(self, output: Data, next_stage: Stage | None) -> Data:
        """Convert one stage's output into the next stage's input."""
        if isinstance(output, SfmOutput):
            self._last_sfm_output = output
            return GaussiansInput(
                sfm_output=output,
                images_dir=self.workspace.images_dir,
            )
        if isinstance(output, GaussiansOutput):
            self._last_gaussians_output = output
            if isinstance(next_stage, BlenderStage):
                return BlenderInput(
                    gaussians_output=output,
                    blend_output=self.workspace.root / "blender" / "scene.blend",
                )
            if self._last_sfm_output is None:
                raise RuntimeError("No SfmOutput available to build VisualizationInput")
            return VisualizationInput(
                gaussians_output=output,
                images_dir=self.workspace.images_dir,
                sfm_output=self._last_sfm_output,
            )
        # VisualizationOutput → next stage must be Blender
        if isinstance(next_stage, BlenderStage):
            if self._last_gaussians_output is None:
                raise RuntimeError("No GaussiansOutput available to build BlenderInput")
            return BlenderInput(
                gaussians_output=self._last_gaussians_output,
                blend_output=self.workspace.root / "blender" / "scene.blend",
            )
        return output

    def _update_manifest(self, stage_name: str, elapsed: float) -> None:
        """Append stage completion info to the workspace manifest."""
        manifest_path = self.workspace.manifest_path
        manifest: dict = {}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())

        stages = manifest.setdefault("stages", {})
        stages[stage_name] = {
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "elapsed_seconds": round(elapsed, 2),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))
