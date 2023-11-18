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


import abc
import subprocess
from typing import Callable


from . import tasks
from . import data
from . import LOGGER


@data.json.JSONData.dataclass
class ProcessABC(tasks.Task):
    command: str = data.field(default_factory=str)
    returncode: int = data.field(default_factory=int)
    stdout: str = data.field(default_factory=str)
    stderr: str = data.field(default_factory=str)

    def __post_init__(self):
        super().__post_init__()
        self._process: subprocess.Popen | None = None

    @abc.abstractmethod
    def terminate(self):
        pass

    def _reset_process(self):
        self._process = None


@data.dataclass
class StreamingProcessABC(ProcessABC):
    def __post_init__(self):
        self.stdout_callback: Callable[[str], None] | None = None
        self.stderr_callback: Callable[[str], None] | None = None
        return super().__post_init__()
