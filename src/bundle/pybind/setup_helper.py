import logging
import os
from pathlib import Path

from setuptools import setup as standard_setup

from .config import PybindConfig
from .core import PybindProject
from bundle.core import tracer

logger = logging.getLogger(__name__)


def setup(invoking_file: str | Path, **kwargs):
    """
    Replacement for setuptools.setup:
      - Reads [tool.pybind11] from pyproject.toml next to invoking_file
      - Applies setuptools_scm for versioning
      - Honors BUILD_PARALLEL
      - Registers any plugins passed via `plugins=[...]`
    """
    if "BUILD_PARALLEL" in os.environ:
        try:
            kwargs["parallel"] = int(os.environ["BUILD_PARALLEL"])
        except ValueError:
            logger.warning("BUILD_PARALLEL must be an integer; ignoring.")

    # locate pyproject.toml
    project_root = Path(invoking_file).parent.resolve()
    pyproject_file = project_root / "pyproject.toml"
    logger.debug("invoking_file=%s\nproject_root=%s\npyproject_file=%s", invoking_file, project_root, pyproject_file)

    # load config
    config = PybindConfig.load_toml(pyproject_file)

    # build project
    project = PybindProject(config.modules, project_root)

    # plugins
    for plugin in kwargs.pop("plugins", []):
        project.register_plugin(plugin)

    # collect extensions
    ext_modules = kwargs.setdefault("ext_modules", [])
    ext_modules.extend(tracer.Sync.call_raise(project.get_extensions))

    # delegate to setuptools
    standard_setup(**kwargs)
