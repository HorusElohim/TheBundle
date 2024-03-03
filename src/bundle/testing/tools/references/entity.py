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

from datetime import date, datetime
from pathlib import Path
from uuid import UUID, uuid5

from .... import core
from .data import TestComplexData

_DEFAULT_BORN_TIME = 1709476008724944900

JSON_ENCODERS = {
    Path: lambda v: str(v),
    datetime: lambda v: v.isoformat(),
    date: lambda v: v.isoformat(),
}

NAMESPACE = UUID("54681692-1234-5678-1234-567812345678")
UNIQUE_GENERATOR_ACTIVE = True


def _static_identifier():
    return core.entity.Identifier(index=1, uuid=str(uuid5(NAMESPACE, str(1))))


class TestEntity(core.Entity):
    born_time: int = core.data.Field(default=_DEFAULT_BORN_TIME)
    identifier: core.entity.Identifier = core.data.Field(default_factory=_static_identifier)
    version: str = core.data.Field(default="testing")


class NestedModel(TestEntity):
    id: int = core.data.Field(default=0)
    info: str = core.data.Field(default="")
    timestamp: datetime = core.data.Field(default_factory=lambda: datetime(1991, 12, 28))
    model_config = core.data.configuration(json_encoders=JSON_ENCODERS)


class RecursiveModel(TestEntity):
    children: None | list["RecursiveModel"] = None
    model_config = core.data.configuration(json_encoders=JSON_ENCODERS)


class TestComplexEntity(TestEntity):
    string_field: str = core.data.Field(default="")
    int_field: int = core.data.Field(default=1)
    float_field: float = core.data.Field(default=1.0)
    bool_field: bool = core.data.Field(default=False)
    optional_field: None | str = core.data.Field(default=None)
    list_field: list[int] = core.data.Field(default_factory=list)
    set_field: set[str] = core.data.Field(default_factory=set)
    dict_field: dict[str, int] = core.data.Field(default_factory=dict)
    dict_complex_field: dict[str, Path] = core.data.Field(default_factory=dict)
    union_field: int | str = core.data.Field(default=0)
    nested_model: NestedModel = core.data.Field(default_factory=NestedModel)
    nested_model_list: list[NestedModel] = core.data.Field(default_factory=list)
    optional_nested_model: None | NestedModel = core.data.Field(default=None)
    recursive_model: RecursiveModel = core.data.Field(default_factory=RecursiveModel)
    dynamic_default_field: str = core.data.Field(default_factory=lambda: "Dynamic")
    file_path: Path = core.data.Field(default_factory=Path)
    model_config = core.data.configuration(json_encoders=JSON_ENCODERS)

    @core.data.field_validator("int_field")
    def check_positive(cls, value):
        if value <= 0:
            raise ValueError("int_field must be positive")
        return value

    @core.data.model_validator(mode="after")
    def check_dynamic_default_based_on_int_field(self):
        if self.int_field and self.int_field > 10:
            self.dynamic_default_field = "HighValue"
        else:
            self.dynamic_default_field = "LowValue"
        return self


class TestComplexEntityMultipleInheritance(RecursiveModel, TestComplexData):
    born_time: int = core.data.Field(default=_DEFAULT_BORN_TIME)


RecursiveModel.model_rebuild()
TestComplexEntity.model_rebuild()
