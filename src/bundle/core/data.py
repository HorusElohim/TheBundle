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
# flake8: noqa: F401

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Callable, Type, TypeVar

from pydantic import HttpUrl  # noqa
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_serializer,
    field_validator,
    json_schema,
    model_validator,
)
from pydantic.warnings import PydanticDeprecatedSince20

from . import tracer

warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)

__doc__ = """
This module defines a foundational data model framework leveraging Pydantic for robust data validation,
serialization, and deserialization functionalities tailored for complex software systems. It provides
an extendable base `Data` class equipped with utilities for handling JSON data interchange, including
methods for creating model instances from dictionaries or JSON strings/files, serializing models back
to dictionaries or JSON, and generating JSON Schema for model validation.

Key Features:
- Robust data validation and type checking at runtime using Pydantic.
- Easy instantiation of model objects from JSON strings, dictionaries, or files.
- Serialization of model instances to JSON strings or files with customizable formatting.
- Generation of JSON Schema for model validation purposes, supporting different modes of schema generation.
- Integrated logging for debugging and error tracking, enhancing development and maintenance workflows.

Intended Use:
This module is designed for developers seeking a structured and efficient approach to managing data
models in applications that heavily interact with JSON data formats, requiring rigorous validation and
flexible serialization/deserialization capabilities. It is particularly useful in web services, APIs,
data processing pipelines, and configuration management systems where data integrity and easy
interoperability are paramount.

Copyright 2024 HorusElohim

Licensed under the Apache License, Version 2.0. See LICENSE file for terms.
"""


D = TypeVar("D", bound="Data")


def _internal_configuration(**kwargs):
    """
    Internal helper function to configure Pydantic model settings.

    Args:
        **kwargs: Arbitrary keyword arguments for model configuration options.

    Returns:
        A `ConfigDict` instance with the provided configuration settings.

    Raises:
        AssertionError: If `json_encoders` is provided but is not a dictionary.
    """
    if "json_encoders" in kwargs:
        if kwargs["json_encoders"] is not None:
            assert isinstance(
                kwargs["json_encoders"], dict
            ), "json_encoder must be dict[type, Callable[value]] where the callable defines the serialization function"
    return ConfigDict(**kwargs)


def configuration(
    arbitrary_types_allowed: bool = True,
    from_attributes: bool = True,
    extra: str = "forbid",
    json_encoders: dict[type, Callable] | None = None,
):
    """
    Public interface to define configuration settings for Pydantic models.

    Args:
        arbitrary_types_allowed (bool): Allows arbitrary types, defaults to True.
        from_attributes (bool): Whether to use model attributes for configuration, defaults to True.
        extra (str): Policy for extra attributes, defaults to "forbid".
        json_encoders (dict[type, Callable] | None): Custom JSON encoders for specific types.

    Returns:
        A `ConfigDict` instance with the specified configuration settings.
    """
    return _internal_configuration(
        arbitrary_types_allowed=arbitrary_types_allowed,
        from_attributes=from_attributes,
        extra=extra,
        json_encoders=json_encoders,
    )


class Data(BaseModel):
    """
    Base data model class, providing utilities for serialization and deserialization
    from/to JSON, along with JSON Schema generation.

    Attributes:
        model_config: Default model configuration settings.
    """

    model_config = configuration()

    # Test name is used to differentiate the same Data with different test results
    __test_name: str = PrivateAttr(default="base")

    @classmethod
    @tracer.Async.decorator.call_raise
    async def from_dict(cls: Type[D], data: dict) -> D:
        """
        Create an instance of the model from a dictionary.

        Args:
            data (dict): The data dictionary from which to create the model instance.

        Returns:
            An instance of the model.

        Raises:
            Exception: If the model instantiation fails.
        """
        return cls(**data)

    @tracer.Async.decorator.call_raise
    async def as_dict(self) -> dict:
        """
        Create an instance of the model from a JSON file.

        Args:
            json_path (Path): The path to the JSON file.

        Returns:
            An instance of the model.

        Raises:
            Exception: If the model instantiation from the JSON file fails.
        """
        return self.model_dump()

    @classmethod
    @tracer.Async.decorator.call_raise
    async def _from_json_path(cls: Type[D], json_path: Path) -> D:
        json_str = await tracer.Async.call_raise(json_path.read_text)
        return await cls._from_json_str(json_str)

    @classmethod
    @tracer.Async.decorator.call_raise
    async def _from_json_str(cls: Type[D], json_str: str) -> D:
        """
        Create an instance of the model from a JSON string.

        Args:
            json_str (str): The JSON string.

        Returns:
            An instance of the model.

        Raises:
            Exception: If the model instantiation from the JSON string fails.
        """
        return await tracer.Async.call_raise(cls.model_validate_json, json_str)

    @classmethod
    @tracer.Async.decorator.call_raise
    async def from_json(cls: Type[D], json_source: str | Path) -> D:
        """
        Create an instance of the model from either a JSON string or a path to a JSON file.

        Args:
            json_source (str | Path): The JSON string or path to the JSON file.

        Returns:
            An instance of the model.

        Raises:
            RuntimeError: If the `json_source` is neither a string nor a Path instance.
            Exception: If the model instantiation from the JSON source fails.
        """
        if isinstance(json_source, str):
            return await cls._from_json_str(json_source)
        elif isinstance(json_source, Path):
            return await cls._from_json_path(json_source)
        else:
            raise RuntimeError(f"Unsupported json_source={json_source}")

    @tracer.Async.decorator.call_raise
    async def as_json(self) -> str:
        """
        Serialize the model instance to a JSON string.

        Returns:
            A JSON string representation of the model instance.

        Raises:
            Exception: If serialization to JSON fails.
        """
        return self.model_dump_json(indent=4)

    @tracer.Async.decorator.call_raise
    async def dump_json(self, path: Path) -> None:
        """
        Write the JSON representation of the model instance to a file.

        Args:
            path (Path): The file path where the JSON data will be saved.

        Raises:
            Exception: If writing to the file fails.
        """
        json_str = await self.as_json()
        await tracer.Async.call_raise(path.write_text, json_str, encoding="utf-8")

    @classmethod
    @tracer.Async.decorator.call_raise
    async def as_jsonschema(cls, mode: json_schema.JsonSchemaMode = "serialization") -> dict:
        """
        Generate the JSON Schema of the model.

        Args:
            mode (json_schema.JsonSchemaMode): The mode of the JSON Schema, defaults to "serialization".

        Returns:
            A dictionary representing the JSON Schema of the model.

        Raises:
            Exception: If generating the JSON Schema fails.
        """
        return cls.model_json_schema(mode=mode)

    @classmethod
    @tracer.Async.decorator.call_raise
    async def as_jsonschema_str(cls, mode: json_schema.JsonSchemaMode = "serialization") -> str:
        """
        Serialize the JSON Schema of the model to a JSON string.

        Args:
            mode (json_schema.JsonSchemaMode): The mode of the JSON Schema, defaults to "serialization".

        Returns:
            A JSON string representation of the model's JSON Schema.

        Raises:
            Exception: If serializing the JSON Schema to a string fails.
        """
        schema = await cls.as_jsonschema(mode)
        return await tracer.Async.call_raise(json.dumps, schema, indent=4)

    @tracer.Async.decorator.call_raise
    async def dump_jsonschema(self, path: Path, mode: json_schema.JsonSchemaMode = "serialization") -> None:
        """
        Write the JSON Schema of the model to a file.

        Args:
            path (Path): The file path where the JSON Schema will be saved.
            mode (json_schema.JsonSchemaMode): The mode of the JSON Schema, defaults to "serialization".

        Raises:
            Exception: If writing the JSON Schema to the file fails.
        """
        schema_str = await self.as_jsonschema_str(mode)
        await tracer.Async.call_raise(path.write_text, schema_str, encoding="utf-8")
