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

import json as js
from pathlib import Path
import logging
import abc
import jsonschema
from typing import Any, Dict, Union, Type, Set, get_type_hints
import pickle
import traceback
import dataclasses
from . import Dataclass, dataclass, fields, check_file_exist, logger


def is_json_serializable(value: Any) -> bool:
    """Check if a value is JSON serializable."""
    try:
        js.dumps(value, cls=js.JSONEncoder)
        return True
    except (TypeError, OverflowError):
        return False


LOGGER = logging.getLogger(__name__)

DEFAULT_SCHEMA = "http://json-schema.org/draft-07/schema#"


class CustomJSONEncoder(js.JSONEncoder):
    """Extended JSON encoder to handle special data types using pickle for non-JSON serializable objects."""

    def default(self, obj: Any) -> Any:
        # Convert custom dataclass objects to dictionaries
        LOGGER.debug(f"CustomJSONEncoder for {type(obj)}")
        if isinstance(obj, Dataclass):
            return obj.as_dict()
        if isinstance(obj, Path):
            return {"_path_": str(obj)}
        try:
            # Try to serialize using the parent class method
            return super().default(obj)
        except TypeError:
            # If the object is not JSON serializable, use pickle
            pickled_data = pickle.dumps(obj).hex()
            return {"_pickle_": pickled_data}


class CustomJSONDecoder(js.JSONDecoder):
    """Custom JSON decoder to handle pickled data types."""

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, dct: Dict) -> Any:
        if dct.get("_pickle_"):
            return pickle.loads(bytes.fromhex(dct["_pickle_"]))
        if dct.get("_path_"):
            return Path(dct["_path_"])
        return dct


class JSONDataABC(abc.ABC):
    """Abstract base class representing objects that can be serialized to and from JSON."""

    @abc.abstractclassmethod
    def from_json(cls: Type[JSONData], path: Union[str, Path]) -> JSONData:
        """Deserialize from a JSON file."""
        pass

    @abc.abstractmethod
    def dump_json(self, path: Union[str, Path]) -> None:
        """Serialize to a JSON file."""
        pass

    @property
    @abc.abstractmethod
    def json_encoder(self) -> CustomJSONEncoder:
        """Get the JSON encoder for this class."""
        pass


@dataclass(unsafe_hash=True)
class JSONData(JSONDataABC, Dataclass):
    """A dataclass that can be serialized to and from JSON."""

    json_decoder = CustomJSONDecoder
    json_encoder = CustomJSONEncoder

    @staticmethod
    def load_json_file(json_path: Union[Path, str], decoder: js.JSONDecoder = CustomJSONDecoder) -> Union[dict, None]:
        json_path = check_file_exist(json_path, not_exist_raise=True)
        try:
            with Path(json_path).open("r") as file:
                obj_dict = js.load(file, cls=decoder)
                LOGGER.debug(f"{json_path=} {logger.Emoji.success}")
                return obj_dict
        except jsonschema.ValidationError:
            LOGGER.error(f"{json_path=} {logger.Emoji.failed} \n{traceback.format_exc()}")
            return None

    @staticmethod
    def dump_json_file(
        obj_dict: Dict,
        path: Union[Path, str],
        encoder: js.JSONEncoder = CustomJSONEncoder,
    ) -> Union[dict, None]:
        path = check_file_exist(path)
        try:
            with Path(path).open("w") as file:
                js.dump(obj_dict, file, indent=4, cls=encoder)
                LOGGER.debug(f"{path=} {logger.Emoji.success}")
                return obj_dict
        except jsonschema.ValidationError:
            LOGGER.error(f"{path=} {logger.Emoji.failed} \n{traceback.format_exc()}")
            return None

    @classmethod
    def from_json(cls: Type[JSONData], path: Union[str, Path]) -> JSONData:
        """Load the dataclass from a JSON file."""
        obj_dict = JSONData.load_json_file(json_path=path, decoder=cls.json_decoder)
        LOGGER.debug(f"{path=}{logger.Emoji.success}{obj_dict}")
        return cls.from_dict(obj_dict)

    def dump_json(self, path: Union[str, Path]) -> None:
        """Save the dataclass to a JSON file."""
        self.dump_json_file(obj_dict=self.as_dict(), path=path, encoder=self.json_encoder)
        LOGGER.debug(f"{path=}{logger.Emoji.success}")

    def as_json(self) -> None:
        """Convert the dataclass to a JSON string."""
        return js.dumps(self.as_dict(), indent=4, cls=self.json_encoder)

    @classmethod
    def generate_jsonschema(
        cls,
        target_cls: Type[JSONData] = None,
        processed_classes: Set[Type] = None,
    ) -> Dict[str, Any]:
        """Generate a JSON schema for this or a given dataclass."""
        if processed_classes is None:
            processed_classes = set()

        target_cls = target_cls or cls
        if target_cls in processed_classes:
            return {"type": "object", "title": target_cls.__name__}

        processed_classes.add(target_cls)

        if not dataclasses.is_dataclass(target_cls):
            raise TypeError(f"Expected a dataclass type, got {target_cls}")

        type_to_schema = {
            int: "integer",
            float: "number",
            str: "string",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        def get_pickled_schema() -> Dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "_pickle_": {"type": "boolean", "const": True},
                    "data": {"type": "string"},
                },
                "required": ["_pickle_", "data"],
            }

        def get_schema_for_type(type_hint: Type) -> Dict[str, Any]:
            LOGGER.debug(f"Working on {type_hint=}")
            if type_hint in type_to_schema:
                return {"type": type_to_schema[type_hint]}
            elif getattr(type_hint, "__origin__", None) == list:
                item_type = type_hint.__args__[0]
                return {"type": "array", "items": get_schema_for_type(item_type)}
            elif dataclasses.is_dataclass(type_hint):
                LOGGER.debug(f"Recursive call on dataclass")
                return cls.generate_jsonschema(type_hint, processed_classes)
            else:
                # Fallback for other non-dataclass types
                return get_pickled_schema()

        properties = {key: get_schema_for_type(type_hint) for key, type_hint in get_type_hints(target_cls).items()}

        required_fields = [f.name for f in fields(target_cls)]

        return {
            "$schema": DEFAULT_SCHEMA,
            "title": target_cls.__name__,
            "type": "object",
            "properties": properties,
            "required": required_fields,
        }

    @classmethod
    def to_jsonschema(cls, path: Union[str, Path]):
        """Save a JSON schema for this dataclass."""

        report = f"to_schema({path})"
        try:
            with Path(path).open("w") as file:
                js.dump(cls.generate_jsonschema(), file, indent=4)
                LOGGER.debug(f"{report}{logger.Emoji.success} ")
        except Exception:
            LOGGER.error(f"{report} {logger.Emoji.failed} \n{traceback.format_exc()}")

    @classmethod
    def schema_validation(
        cls: Type[JSONData],
        json_path: Union[Path, str, None] = None,
        jsonschema_path: Union[Path, str, None] = None,
    ) -> bool:
        """Validate JSON data against the schema."""
        # Load the data from the provided path
        report = f"schema_validation{json_path=}"
        if json_path:
            with Path(json_path).open("r") as file:
                data = js.load(file)
        else:
            data = cls.as_dict()

        # Get the schema for the current dataclass
        if jsonschema_path:
            with Path(jsonschema_path).open("r") as file:
                schema = js.load(file)
        else:
            schema = cls.generate_jsonschema()

        # Validate the data against the schema
        try:
            jsonschema.validate(data, schema)
            LOGGER.debug(f"{report} {logger.Emoji.success}")
            return True
        except jsonschema.ValidationError:
            LOGGER.error(f"{report} {logger.Emoji.failed} \n{traceback.format_exc()}")
            return False

    def is_valid_by_jsonschema(self, jsonschema_path: Union[Path, str, None] = None) -> bool:
        """Validate JSON data against the schema."""
        try:
            # Load the data from the provided path
            data = self.as_dict()
            # Get the schema for the current dataclass
            jsonschema_dict = JSONData.load_json_file(jsonschema_path) if jsonschema_path else self.generate_jsonschema()
            # Validate the data against the schema
            jsonschema.validate(data, jsonschema_dict)
            LOGGER.debug(f"{jsonschema_path=} {logger.Emoji.success}")
            return True
        except jsonschema.ValidationError:
            LOGGER.error(f"{jsonschema_path=} {logger.Emoji.failed} \n{traceback.format_exc()}")
            return False
