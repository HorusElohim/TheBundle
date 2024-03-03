from __future__ import annotations

from .... import core
from .data import TestComplexData
from datetime import datetime, date
from pathlib import Path

_DEFAULT_BORN_TIME = 1709476008724944900

JSON_ENCODERS = {
    Path: lambda v: str(v),
    datetime: lambda v: v.isoformat(),
    date: lambda v: v.isoformat(),
}


class NestedModel(core.Atom):
    id: int = core.data.Field(default=0)
    info: str = core.data.Field(default="")
    timestamp: datetime = core.data.Field(default_factory=lambda: datetime(1991, 12, 28))
    born_time: int = core.data.Field(default=_DEFAULT_BORN_TIME)
    model_config = core.data.configuration(json_encoders=JSON_ENCODERS)


class RecursiveModel(core.data.Data):
    name: str = core.data.Field(default="")
    children: None | list["RecursiveModel"] = None
    model_config = core.data.configuration(json_encoders=JSON_ENCODERS)


class TestComplexAtom(core.Atom):
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
    born_time: int = core.data.Field(default=_DEFAULT_BORN_TIME)
    model_config = core.data.configuration(json_encoders=JSON_ENCODERS)

    @core.data.field_validator("int_field")
    def check_positive(cls, value):
        if value <= 0:
            raise ValueError("int_field must be positive")
        return value

    @core.data.model_validator(mode="after")
    def check_dynamic_default_based_on_int_field(self) -> TestComplexAtom:
        if self.int_field and self.int_field > 10:
            self.dynamic_default_field = "HighValue"
        else:
            self.dynamic_default_field = "LowValue"
        return self


class TestComplexAtomMultipleInheritance(core.Atom, TestComplexData):
    born_time: int = core.data.Field(default=_DEFAULT_BORN_TIME)


RecursiveModel.model_rebuild()
