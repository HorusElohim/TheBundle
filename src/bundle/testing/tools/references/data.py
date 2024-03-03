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

from .... import core

JSON_ENCODERS = {
    Path: lambda v: str(v),
    datetime: lambda v: v.isoformat(),
    date: lambda v: v.isoformat(),
}


class TestData(core.data.Data):
    pass


class NestedModel(core.data.Data):
    id: int = core.data.Field(default=0)
    info: str = core.data.Field(default="")
    timestamp: datetime = core.data.Field(default_factory=lambda: datetime(1991, 12, 28))
    model_config = core.data.configuration(json_encoders=JSON_ENCODERS)


class RecursiveModel(core.data.Data):
    name: str = core.data.Field(default="")
    children: None | list["RecursiveModel"] = None
    model_config = core.data.configuration(json_encoders=JSON_ENCODERS)


class TestComplexData(core.data.Data):
    string_field: str = core.data.Field(default="")
    int_field: int = core.data.Field(default=1)
    float_field: float = core.data.Field(default=1.0)
    bool_field: bool = core.data.Field(default=False)
    optional_field: None | str = core.data.Field(default=None)
    list_field: list[int] = core.data.Field(default_factory=list)
    set_field: set[str] = core.data.Field(default_factory=set)
    dict_field: dict[str, int] = core.data.Field(default_factory=dict)
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
    def check_dynamic_default_based_on_int_field(cls, instance: TestComplexData):
        if instance.int_field and instance.int_field > 10:
            instance.dynamic_default_field = "HighValue"
        else:
            instance.dynamic_default_field = "LowValue"
        return instance


RecursiveModel.model_rebuild()
