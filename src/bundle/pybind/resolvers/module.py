from ..resolved.module import ModuleResolved
from ..resolvers.pkgconfig import PkgConfigResolver
from ..specs.module import ModuleSpec


class ModuleResolver:
    def __init__(self, pkgconfig_resolver: PkgConfigResolver | None = None):
        self.pkgconfig_resolver = pkgconfig_resolver or PkgConfigResolver()

    async def resolve(self, spec: ModuleSpec) -> ModuleResolved:
        pkgconfig_result = await self.pkgconfig_resolver.resolve(spec.pkgconfig)
        return ModuleResolved(spec=spec, pkgconfig=pkgconfig_result)
