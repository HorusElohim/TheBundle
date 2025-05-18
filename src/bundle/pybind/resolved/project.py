from bundle.core import data

from ..specs import ProjectSpec
from .module import ModuleResolved


class ProjectResolved(data.Data):
    """
    This class defines the resolved configuration options required to build a pybind11 extension module.
    """

    spec: ProjectSpec
    modules: list[ModuleResolved] = data.Field(default_factory=list)
