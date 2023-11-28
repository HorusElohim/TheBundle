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

import asyncio
from typing import Any
from pathlib import Path
from functools import wraps
import logging

from ... import data, nodes

LOGGER = logging.getLogger(__name__)


@data.dataclass
class TestNodeTask(nodes.NodeTask):
    born_time: int = 1
    id: str = "test-id"

    def exec(self):
        return self.name


@data.dataclass
class TestNodeAsyncTask(nodes.NodeAsyncTask):
    born_time: int = 1
    id: str = "test-id"

    async def exec(self):
        return self.name


@data.dataclass
class TestNodeProcess(nodes.NodeProcess):
    born_time: int = 1
    id: str = "test-id"

    def exec(self, **kwds) -> bool:
        kwds["capture_output"] = True
        kwds["text"] = True
        return super().exec(**kwds)


@data.dataclass
class TestNodeAsyncProcess(nodes.NodeAsyncProcess):
    born_time: int = 1
    id: str = "test-id"


@data.dataclass
class TestNodeStreamingProcess(nodes.NodeStreamingProcess):
    born_time: int = 1
    id: str = "test-id"


@data.dataclass
class TestNodeStreamingAsyncProcess(nodes.NodeStreamingAsyncProcess):
    born_time: int = 1
    id: str = "test-id"
