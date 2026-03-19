"""Sequential pipeline runner for the Recon3D reconstruction chain."""

from __future__ import annotations

import json
import time
from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data
from bundle.core.entity import Entity

from .contracts import GaussiansInput, SfmBackend, SfmInput, Workspace
from .stages.base import Stage
from .stages.gaussians import GaussiansStage
from .stages.sfm import SfmStage

log = logger.get_logger(__name__)


class Pipeline(Entity):
    """Runs a list of stages sequentially, threading each output into the next input.

    After each stage completes, the pipeline writes a ``manifest.json`` into the
    workspace so that ``bundle recon3d status`` can report progress.
    """

    name: str = "recon3d-pipeline"
    workspace: Workspace
    stages: list[Stage] = []

    model_config = Data.model_config.copy()
    model_config["arbitrary_types_allowed"] = True

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def default(
        cls,
        workspace: Workspace,
        sfm_backend: SfmBackend = SfmBackend.COLMAP,
        renderer: str = "3dgut",
        export_usdz: bool = True,
    ) -> Pipeline:
        """Create the standard SfM -> Gaussians pipeline."""
        return cls(
            workspace=workspace,
            stages=[
                SfmStage(backend=sfm_backend),
                GaussiansStage(renderer=renderer, export_usdz=export_usdz),
            ],
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(self) -> dict[str, Data]:
        """Execute all stages in order, returning a map of stage_name -> output."""
        self.workspace.ensure_dirs()
        results: dict[str, Data] = {}
        current_input: Data | None = None

        for stage in self.stages:
            log.info("Running stage: %s", stage.name)

            if not await stage.check_deps():
                raise RuntimeError(f"Stage '{stage.name}' dependencies not met — run check_deps() for details")

            if current_input is None:
                current_input = self._initial_input_for(stage)

            t0 = time.monotonic()
            output = await stage.run(current_input)
            elapsed = time.monotonic() - t0

            log.info("Stage '%s' completed in %.1fs", stage.name, elapsed)
            results[stage.name] = output
            current_input = self._adapt(stage, output)

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
        raise RuntimeError(f"Unknown stage type: {type(stage)}")

    @staticmethod
    def _adapt(prev_stage: Stage, output: Data) -> Data:
        """Convert one stage's output into the next stage's input."""
        from .contracts import SfmOutput

        if isinstance(output, SfmOutput):
            return GaussiansInput(
                sfm_output=output,
                images_dir=output.sparse_dir.parent.parent / "images",
            )
        # Terminal stage — no further adaptation needed
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
