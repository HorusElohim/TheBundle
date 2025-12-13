# Copyright 2024 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

import sys
import time
from uuid import UUID, uuid5

from .. import version
from . import Data, data, logger, utils

LOGGER = logger.get_logger(__name__)

__doc__ = """
This module introduces the `Entity` class, an extension of the `Data` model designed to represent
entities with enhanced capabilities for introspection and optional persistence. The `Entity` class
includes functionalities for tracking creation time, calculating age, and, if enabled, automatically
saving the entity's state to a JSON file upon destruction.

Features:
- Tracking of creation time with nanosecond precision.
- Optional auto-saving to JSON upon destruction, facilitating simple state persistence.
- Introspection capabilities, including access to the entity's class name and age calculation.

Usage:
The `Entity` class is suited for applications that require detailed lifecycle management of entities,
such as in simulation environments, complex data models, or systems where state persistence and introspection are valuable.
"""

NAMESPACE = UUID("54681692-1234-5678-1234-567812345678")
UNIQUE_GENERATOR_ACTIVE = True


def _identifier_generator(start=0, step=1):
    index = start
    while UNIQUE_GENERATOR_ACTIVE:
        index += step
        yield Identifier(index=index, uuid=str(uuid5(NAMESPACE, str(index))))


class Identifier(data.Data):
    index: int
    uuid: str

    @staticmethod
    def next() -> Identifier:
        return next(ENTITY_ID_GENERATOR)


ENTITY_ID_GENERATOR = _identifier_generator()


class Entity(Data):
    """
    An extension of the `Data` model that represents an entity with enhanced introspection
    and optional persistence capabilities. It tracks the entity's creation time and can automatically
    save its state upon destruction if configured to do so.

    Attributes:
        name (str): The name of the entity, with a default value of "Default".
        born_time (int): The timestamp of entity instantiation, in nanoseconds.

    Properties:
        class_name (str): The name of the entity's class.
        age (int): The age of the entity in nanoseconds, calculated from its `born_time`.
    """

    version: str = version
    name: str = data.Field(default="default")
    identifier: Identifier = data.Field(default_factory=Identifier.next)
    born_time: int = data.Field(default_factory=time.time_ns)

    @data.model_validator(mode="after")
    def _init_(cls, entity):
        """
        Logs the creation of an entity instance, triggered after full initialization and validation.

        Args:
            entity: The Entity instance being validated and initialized.

        Returns:
            The unchanged Entity instance, ensuring it passes through the validation process without modifications.
        """
        LOGGER.debug("%s  %s[%s]", logger.Emoji.start, entity.class_name, entity.name)
        return entity

    @property
    def class_name(self) -> str:
        """Returns the class name of the instance."""
        return self.__class__.__name__

    @property
    def age(self) -> int:
        """Calculates and returns the age of the entity in nanoseconds since instantiation."""
        return time.time_ns() - self.born_time

    def __del__(self):
        """
        Destructor method for the Entity class logging the entity's deletion along with its age.
        """
        if sys.meta_path is None or not LOGGER.hasHandlers():
            # Avoid logging if no handlers are attached.
            # This can happen on the last entity when the program is exiting.
            return
        LOGGER.debug("%s  %s[%s] age=%s", logger.Emoji.end, self.class_name, self.name, utils.format_duration_ns(self.age))
