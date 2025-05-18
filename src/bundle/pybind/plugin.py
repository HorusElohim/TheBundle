from abc import ABC, abstractmethod

from .core import PybindModule


class PybindPlugin(ABC):
    @abstractmethod
    async def apply(self, module: PybindModule) -> None:
        """Modify module.config in place."""
        ...
