from bundle.core import data

from .module import ModuleSpec


class ProjectSpec(data.Data):
    """
    Root configuration holding all ModuleConfig entries.
    """

    modules: list[ModuleSpec] = data.Field(default_factory=list)
