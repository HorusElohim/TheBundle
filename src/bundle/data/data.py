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

from typing import List
from typing import Any, Dict, List, Type, TypeVar, Union
from pprint import pformat

from . import dataclass, field, asdict, LOGGER, logger


@dataclass
class Dataclass:
    """
    A utility wrapper around the standard Python dataclass to facilitate easy
    conversions between dataclass instances and dictionaries.

    Attributes:
        dataclass: Reference to the dataclass decorator.
        field: Helper function to define fields with default values or other attributes.
    """

    class_type: str = field(default_factory=str)
    dataclass = dataclass
    field = field

    def __post_init__(self):
        # Set the class_type attribute to the name of the class
        # This will be set for every instance of Dataclass or its subclasses
        self.class_type = self.__class__.__name__

    @staticmethod
    def _is_annotation_present_in_mro(cls, field_name):
        for base_class in cls.__mro__:
            if field_name in getattr(base_class, "__annotations__", {}):
                return True
        return False

    @staticmethod
    def _recursive_dataclass_from_dict(target_class: Dataclass, source_dict: Union[Dict, List]) -> Dataclass:
        """
        Recursively convert a dictionary to a dataclass instance.
        """
        try:
            # Log the expected fields from annotations in the MRO and the actual keys from source_dict
            expected_fields = set()
            if not hasattr(target_class, "__mro__"):
                raise RuntimeError(f"{target_class=} not a class!")
            for base_class in target_class.__mro__:
                expected_fields.update(getattr(base_class, "__annotations__", {}).keys())

            actual_keys = set(source_dict.keys())
            LOGGER.debug(f"Expected fields for {target_class} from MRO: {sorted(expected_fields)}")
            LOGGER.debug(f"Actual keys in source_dict: {sorted(actual_keys)}")

            initialized_fields = {}
            for field in source_dict:
                LOGGER.debug(f"working on field {field}")
                if Dataclass._is_annotation_present_in_mro(target_class, field):
                    field_type = next(
                        (
                            getattr(base_class, "__annotations__", {}).get(field)
                            for base_class in target_class.__mro__
                            if field in getattr(base_class, "__annotations__", {})
                        ),
                        None,
                    )
                    if isinstance(source_dict[field], dict):
                        initialized_fields[field] = Dataclass._recursive_dataclass_from_dict(field_type, source_dict[field])
                    else:
                        initialized_fields[field] = source_dict[field]
                else:
                    # If the field is not in annotations of any base classes, log this information
                    LOGGER.warning(
                        f"Field '%s' is not expected according to the annotations in the MRO of '%s'",
                        field,
                        target_class.__name__,
                    )

            # Log any missing fields
            missing_fields = expected_fields - actual_keys
            if missing_fields:
                msg = f"Missing fields in source_dict that are expected in MRO of target_class: {missing_fields}"
                LOGGER.error(msg)
                raise ValueError(msg)

            return target_class(**initialized_fields)
        except KeyError as e:
            # Key is missing in the dictionary, log an error before raising an exception
            LOGGER.error(f"Key missing in source_dict for the expected field in MRO of target_class: {e}")
            raise ValueError(f"Key missing in source_dict for the expected field in MRO of target_class: {target_class}: {e}")

    @classmethod
    def from_dict(cls: Dataclass, d: Dict[str, Any]) -> Dataclass:
        """
        Create an instance of the dataclass from a dictionary.

        Args:
            d: The dictionary containing data to be converted to a dataclass instance.

        Returns:
            An instance of the Dataclass initialized with data from the dictionary.

        Raises:
            ValueError: If a required key is missing in the dictionary.
            TypeError: If there's a type mismatch or unexpected structure in the dictionary.
        """
        data_class = Dataclass._recursive_dataclass_from_dict(cls, d)
        LOGGER.debug(logger.Emoji.success)
        return data_class

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert the dataclass instance to a dictionary.

        Returns:
            A dictionary representation of the dataclass instance.
        """
        data_dict = asdict(self)
        LOGGER.debug(logger.Emoji.success)
        return data_dict

    def __str__(self) -> str:
        class_header = f"--------\n{self.class_type}\n--------"
        formatted_data = pformat(self.as_dict(), indent=4, width=80, depth=None)
        return f"{class_header}\n{formatted_data}\n--------"

    def __hash__(self) -> int:
        return hash(self.as_dict())
