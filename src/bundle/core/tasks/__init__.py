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
from typing import Type
from .. import data

LOGGER = logging.getLogger(__name__)
ns_to_ms = lambda ns: f"{ns * 1e-6:3f}"

from ._abc import TaskABC
from .synchronous import SyncTask
from .asynchronous import AsyncTask


@data.dataclass
class Task(SyncTask):
    Abc = TaskABC
    Async = AsyncTask