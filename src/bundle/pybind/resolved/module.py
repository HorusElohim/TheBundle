from bundle.core import data

from ..specs import ModuleSpec
from .pkgconfig import PkgConfigResolved


class ModuleResolved(data.Data):
    """
    This class defines the resolved configuration options required to build a pybind11 extension module.
    In addition of ModuleSpec, add the resolved pkg-config information.
    """

    spec: ModuleSpec
    pkgconfig: PkgConfigResolved = data.Field(default_factory=PkgConfigResolved)
