"""Defines PybindPlugin (ABC)"""

from abc import ABC, abstractmethod

from ..resolved import ModuleResolved
from ..specs import ModuleSpec


class PybindPluginSpec(ABC):
    @abstractmethod
    async def apply(self, module: ModuleSpec) -> ModuleSpec:
        """
        Applies plugin logic to a module specification or a resolved module.
        This method is asynchronous to allow for I/O operations within plugins.
        It should return the (potentially modified) module. For immutability,
        it's recommended to return a new instance if changes are made.
        """
        raise NotImplementedError("Plugin 'apply' method must be implemented by subclasses.")


class PybindPluginResolved(ABC):
    @abstractmethod
    async def apply(self, module: ModuleResolved) -> ModuleResolved:
        """
        Applies plugin logic to a resolved module.
        This method is asynchronous to allow for I/O operations within plugins.
        It should return the (potentially modified) module. For immutability,
        it's recommended to return a new instance if changes are made.
        """
        raise NotImplementedError("Plugin 'apply' method must be implemented by subclasses.")
