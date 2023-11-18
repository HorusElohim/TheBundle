# Copyright 2023 HorusElohim

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


import logging
from .. import data, Path, time, typing, logging, version

LOGGER = logging.getLogger(__name__)


@data.dataclass
class Entity(data.JSONData):
    name: str = data.field(default_factory=str)
    path: Path = data.field(default_factory=Path)
    born_time: int = data.field(default_factory=time.time_ns, compare=False)
    dead_time: int = data.field(default_factory=int)
    auto_save: bool = data.field(default_factory=bool)

    @property
    def age(self) -> int:
        return time.time_ns() - self.born_time

    @property
    def code(self) -> str:
        import inspect

        return inspect.getsource(inspect.getmodule(inspect.currentframe()))

    def __post_init__(self):
        super().__post_init__()  # Ensure any parent class post-init actions are performed
        self.name = self.name if self.name else "Default"
        LOGGER.debug("❤️  %s.%s in %s", self.class_type, self.name, self.path)

    def __del__(self):
        if self.auto_save:
            try:
                self.dead_time = time.time_ns()
                self.dump_json(self.path / f"{self.__class__.__name__}_{version}.json")
            except Exception as ex:
                if LOGGER:
                    LOGGER.error(f"Exception: {ex}")
        if LOGGER:
            LOGGER.debug("%s.%s age=%d 💀", self.class_type, self.name, self.age)

    def move(self, new_path: typing.Union[Path, str]):
        """
        Update the entity's path.

        :param new_path: The new path (as a Path object or a string) to update the entity's path to.
        """
        # Absolute and Relative
        # Update the entity's path
        self.path = self.path.parent / new_path if not Path(new_path).is_absolute() else new_path
