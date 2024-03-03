import time
from pathlib import Path

from . import CORE_LOGGER, logger, data, utils, Data
from .. import version

__doc__ = """
This module introduces the `Atom` class, an extension of the `Data` model designed to represent
entities with enhanced capabilities for introspection and optional persistence. The `Atom` class
includes functionalities for tracking creation time, calculating age, and, if enabled, automatically
saving the entity's state to a JSON file upon destruction.

Features:
- Tracking of creation time with nanosecond precision.
- Optional auto-saving to JSON upon destruction, facilitating simple state persistence.
- Introspection capabilities, including access to the entity's class name, age calculation, and source code inspection.

Usage:
The `Atom` class is suited for applications that require detailed lifecycle management of entities,
such as in simulation environments, complex data models, or systems where state persistence and introspection are valuable.
"""


class Atom(Data):
    """
    An extension of the `Data` model that represents an entity with enhanced introspection
    and optional persistence capabilities. It tracks the entity's creation time and can automatically
    save its state upon destruction if configured to do so.

    Attributes:
        name (str): The name of the atom, with a default value of "Default".
        path (Path): The filesystem path associated with the atom, used for auto-saving.
        born_time (int): The timestamp of atom instantiation, in nanoseconds.
        dead_time (int): The timestamp of atom destruction, in nanoseconds, set upon auto-saving.
        auto_save (bool): A flag indicating whether the atom should be auto-saved upon destruction.

    Properties:
        class_name (str): The name of the atom's class.
        age (int): The age of the atom in nanoseconds, calculated from its `born_time`.
        code (str): The source code of the module in which the atom is defined, if accessible.

    Methods:
        move(new_path: Path | str): Updates the atom's associated filesystem path.
    """

    name: str = data.Field(default="Default")
    path: Path = data.Field(default_factory=Path)
    born_time: int = data.Field(default_factory=time.time_ns)
    dead_time: int = data.Field(default=0)
    auto_save: bool = data.Field(default=False)

    @data.model_validator(mode="after")
    def log_creation(cls, atom):
        """
        Logs the creation of an Atom instance, triggered after full initialization and validation.

        Args:
            atom: The Atom instance being validated and initialized.

        Returns:
            The unchanged Atom instance, ensuring it passes through the validation process without modifications.
        """
        CORE_LOGGER.debug("%s  %s[%s] path=%s", logger.Emoji.born, atom.class_name, atom.name, atom.path)
        return atom

    @property
    def class_name(self) -> str:
        """Returns the class name of the instance."""
        return self.__class__.__name__

    @property
    def age(self) -> int:
        """Calculates and returns the age of the atom in nanoseconds since instantiation."""
        return time.time_ns() - self.born_time

    @property
    def code(self) -> str:
        """
        Inspects and returns the source code of the module where the atom is defined.

        Returns:
            The source code as a string, if available; otherwise, an empty string.
        """
        import inspect

        if frame := inspect.currentframe():
            if module := inspect.getmodule(frame):
                return inspect.getsource(module)
        return ""

    def __post_init__(self):
        """
        Logs the creation of the Atom instance immediately after its initialization.
        """
        CORE_LOGGER.debug("%s  %s[%s] path=%s", logger.Emoji.born, self.class_name, self.name, self.path)

    def __del__(self):
        """
        Destructor method for the Atom class, handling auto-saving behavior if enabled
        and logging the atom's deletion along with its age.
        """
        if self.auto_save:
            try:
                self.dead_time = time.time_ns()
                self.dump_json(self.path / f"{self.__class__.__name__}_{version}.json")
            except Exception as ex:
                CORE_LOGGER.error("%s  Exception: %s", logger.Emoji.failed, ex)
        CORE_LOGGER.debug(
            "%s  %s[%s] age=%s", logger.Emoji.dead, self.class_name, self.name, utils.format_duration_ns(self.age)
        )

    def move(self, new_path: Path | str):
        """
        Updates the file system path associated with the atom.

        Args:
            new_path (Path | str): The new path to assign to the atom. If `new_path` is a relative
                                   path, it is resolved against the current parent directory of the
                                   atom's path; if absolute, it is set directly.
        """
        self.path = self.path.parent / new_path if not Path(new_path).is_absolute() else Path(new_path)
