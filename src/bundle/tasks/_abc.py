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


from __future__ import annotations

import abc
import time

from . import LOGGER
from .. import data, entity


@data.dataclass(unsafe_hash=True)
class TaskABC(entity.Entity):
    exec_start_time: int = data.field(default_factory=int)
    exec_end_time: int = data.field(default_factory=int)

    @property
    def executed(self) -> bool:
        return all(a > 0 for a in (self.exec_end_time, self.exec_start_time))

    @property
    def duration(self) -> int:
        return self.exec_end_time - self.exec_start_time if self.executed else -1

    @property
    def elapsed(self) -> int:
        return time.time_ns() - self.exec_start_time if self.executed else -1

    @abc.abstractmethod
    def exec(self, *args, **kwds):
        pass
