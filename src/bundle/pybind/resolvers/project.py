import asyncio

from ..resolved.project import ProjectResolved
from ..resolvers.module import ModuleResolver
from ..specs.project import ProjectSpec


class ProjectResolver:
    def __init__(self, module_resolver: ModuleResolver | None = None):
        self.module_resolver = module_resolver or ModuleResolver()

    async def resolve(self, project_spec: ProjectSpec) -> ProjectResolved:
        tasks = [self.module_resolver.resolve(module_spec) for module_spec in project_spec.modules]
        return ProjectResolved(spec=project_spec, modules=list(await asyncio.gather(*tasks)))
