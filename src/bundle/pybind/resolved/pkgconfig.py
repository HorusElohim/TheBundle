from bundle.core import data

from ..specs import PkgConfigSpec


class PkgConfigResult(data.Data):
    name: str = data.Field(default_factory=str)
    include_dirs: list[str] = data.Field(default_factory=list)
    compile_flags: list[str] = data.Field(default_factory=list)
    library_dirs: list[str] = data.Field(default_factory=list)
    libraries: list[str] = data.Field(default_factory=list)
    link_flags: list[str] = data.Field(default_factory=list)


class PkgConfigResolved(data.Data):
    spec: PkgConfigSpec
    resolved: list[PkgConfigResult] = data.Field(default_factory=list)
