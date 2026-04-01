"""Blender stage — base class and I/O contracts.

Takes a GaussiansOutput (PLY path) and produces a ``.blend`` file via a
headless Blender run.  The stage is optional: it only participates in the
pipeline when Blender is discoverable on the host.
"""

from __future__ import annotations

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

    The stage writes a temporary Python script, executes it via
    ``bundle.blender.runtime.BlenderSession``, then cleans up.
    """

    name: str = "blender"

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

        script_src = _build_import_script(inp, render_dir)

        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "recon3d_blender_import.py"
            script_path.write_text(script_src, encoding="utf-8")

            log.info(
                "Importing PLY %s → %s (render=%s)",
                inp.gaussians_output.ply_path,
                inp.blend_output,
                inp.render,
            )

            req = BlenderLaunchRequest(
                executable=str(env.blender_executable),
                args=["--background", "--python", str(script_path)],
            )
            await BlenderSession(req).run()

        output = BlenderOutput(blend_path=inp.blend_output, render_dir=render_dir if inp.render else None)
        if not output.validate_exists():
            raise RuntimeError(f"Blender ran but did not produce the expected .blend file: {inp.blend_output}")
        log.info("Blender stage complete: %s", inp.blend_output)
        return output


# ---------------------------------------------------------------------------
# Script builder
# ---------------------------------------------------------------------------


def _build_import_script(inp: BlenderInput, render_dir: Path | None) -> str:
    """Generate a Blender Python script that imports the PLY and saves the scene."""
    # Use repr() for all path strings — safe against quotes, backslashes, and spaces.
    ply_path = repr(str(inp.gaussians_output.ply_path))
    blend_out = repr(str(inp.blend_output))
    render_out = repr(str(render_dir)) if render_dir else "None"
    engine = repr(inp.engine)
    do_render = repr(inp.render)

    return f"""\
import bpy

# Clear the default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import the PLY point cloud
bpy.ops.wm.ply_import(filepath={ply_path})

imported = bpy.context.selected_objects[:]
if imported:
    for obj in imported:
        obj.name = "GaussianSplat"
    bpy.context.view_layer.objects.active = imported[0]

# Optional render
if {do_render} and {render_out}:
    scene = bpy.context.scene
    scene.render.engine = {engine}
    scene.render.filepath = {render_out} + "/"
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)

# Save .blend
bpy.ops.wm.save_as_mainfile(filepath={blend_out})
print("recon3d-blender: saved", {blend_out})
"""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_blender_stage() -> BlenderStage:
    return BlenderStage()
