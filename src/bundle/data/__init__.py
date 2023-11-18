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

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .. import logger

LOGGER = logger.getLogger(__name__)


def check_file_exist(path: str | Path, not_exist_raise=False) -> Path:
    if not isinstance(path, Path | str):
        raise ValueError(f"{type(path)=}, instead of [Path | str]")
    path = Path(path)
    if not_exist_raise and not path.exists():
        raise ValueError(f"{path=}: {logs.Emoji.failed} NOT EXIST")
    return path


from .data import Dataclass
from .json import JSONData
