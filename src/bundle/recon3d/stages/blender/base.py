"""Blender stage — base class and I/O contracts.

Takes a GaussiansOutput (PLY path) and produces a ``.blend`` file via a
headless Blender run.  The stage is optional: it only participates in the
pipeline when Blender is discoverable on the host.

Blender-side logic lives in ``scripts/`` as standalone ``.py`` files loaded
via ``--python``.  Parameters are passed as a JSON sidecar; no string
interpolation on the host side.

Extending
---------
Subclass ``BlenderStage``, set ``script_name`` to a script in ``scripts/``,
and override ``_build_params`` to supply the script's expected keys::

    class BlenderTurntableStage(BlenderStage):
        name: str = "blender_turntable"
        script_name: str = "render_turntable"

        def _build_params(self, inp, render_dir):
            return {"blend_path": str(inp.blend_path), "frames": inp.frames, ...}
"""

from __future__ import annotations

import importlib.resources as pkg_resources
import json
import tempfile
from pathlib import Path
from typing import Literal

from bundle.core import logger
from bundle.core.data import Data

from ..base import Stage
from ..gaussians.base import GaussiansOutput

log = logger.get_logger(__name__)


# ---------------------------------------------------------------------------
# I/O contracts
# ---------------------------------------------------------------------------


class BlenderInput(Data):
    """Input contract for the Blender import stage."""

    gaussians_output: GaussiansOutput
    blend_output: Path
    render: bool = False
    engine: Literal["EEVEE", "CYCLES"] = "EEVEE"
    render_dir: Path | None = None


class BlenderOutput(Data):
    """Output contract from the Blender import stage."""

    blend_path: Path
    render_dir: Path | None = None

    def validate_exists(self) -> bool:
        if not self.blend_path.exists():
            log.warning("BlenderOutput missing: %s", self.blend_path)
            return False
        return True


# ---------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------


class BlenderStage(Stage):
    """Imports a 3DGS PLY into Blender headless and saves a ``.blend`` file.

    Subclasses override ``script_name`` and ``_build_params`` to drive a
    different Blender script without touching the run machinery.
    """

    name: str = "blender"
    script_name: str = "ply_to_blend"

    # -- Extensibility hooks ------------------------------------------------

    def _build_params(self, inp: BlenderInput, render_dir: Path | None) -> dict:
        """Return the JSON-serializable params dict for the Blender script."""
        return {
            "ply_path": str(inp.gaussians_output.ply_path),
            "blend_out": str(inp.blend_output),
            "render_out": str(render_dir) if render_dir else None,
            "engine": inp.engine,
            "do_render": inp.render,
        }

    def _load_script(self) -> str:
        """Read the Blender-side script from the shipped ``scripts/`` package."""
        return (
            pkg_resources.files("bundle.recon3d.stages.blender.scripts")
            .joinpath(f"{self.script_name}.py")
            .read_text(encoding="utf-8")
        )

    # -- Deps / run ---------------------------------------------------------

    async def check_deps(self) -> bool:
        """Return True if a usable Blender installation is discoverable."""
        try:
            from bundle.blender.runtime import discover_default_environment

            await discover_default_environment()
            return True
        except Exception:
            log.warning("Blender not found — skipping blender stage")
            return False

    async def run(self, input: Data) -> Data:
        assert isinstance(input, BlenderInput)
        return await self._run(input)

    async def _run(self, inp: BlenderInput) -> BlenderOutput:
        from bundle.blender.runtime import discover_default_environment
        from bundle.blender.runtime.session import BlenderLaunchRequest, BlenderSession

        env = await discover_default_environment()

        inp.blend_output.parent.mkdir(parents=True, exist_ok=True)

        render_dir = inp.render_dir
        if inp.render and render_dir is None:
            render_dir = inp.blend_output.parent / "renders"
        if render_dir is not None:
            render_dir.mkdir(parents=True, exist_ok=True)

        params = self._build_params(inp, render_dir)
        script_text = self._load_script()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script_path = tmp_path / f"{self.script_name}.py"
            params_path = tmp_path / "params.json"

            script_path.write_text(script_text, encoding="utf-8")
            params_path.write_text(json.dumps(params), encoding="utf-8")

            log.info(
                "Running Blender script %r: %s → %s (render=%s)",
                self.script_name,
                inp.gaussians_output.ply_path,
                inp.blend_output,
                inp.render,
            )

            req = BlenderLaunchRequest(
                executable=str(env.blender_executable),
                args=["--background", "--python", str(script_path), "--", str(params_path)],
            )
            await BlenderSession(req).run()

        output = BlenderOutput(blend_path=inp.blend_output, render_dir=render_dir if inp.render else None)
        if not output.validate_exists():
            raise RuntimeError(f"Blender ran but did not produce the expected .blend file: {inp.blend_output}")
        log.info("Blender stage complete: %s", inp.blend_output)
        return output


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_blender_stage() -> BlenderStage:
    return BlenderStage()
