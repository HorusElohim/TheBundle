from ..resolved.pkgconfig import PkgConfigResolved
from ..services.pkgconfig import PkgConfigService
from ..specs.pkgconfig import PkgConfigSpec


class PkgConfigResolver:
    def __init__(self, service: PkgConfigService | None = None):
        self.service = service or PkgConfigService()

    async def resolve(self, spec: PkgConfigSpec) -> PkgConfigResolved:
        return await self.service.resolve(spec)
