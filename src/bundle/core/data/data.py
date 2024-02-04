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

from dataclasses import Field, asdict, dataclass, field, fields
from enum import Enum
from types import UnionType
from typing import Any, Generator, Type, TypeVar, get_args, get_origin, get_type_hints

# Handle all derived Dataclass types
D = TypeVar("D", bound="Dataclass")

SUPPORTED_DATACLASS_SEQUENCE_TYPES = [list, tuple]


def get_sequence_element_type(seq_type):
    """
    Extracts and returns the element type of a given sequence type,
    or type(None) if no type arguments are found.
    """
    args = get_args(seq_type)
    return args[0] if args else type(None)


def is_parameterized_generic(typ):
    """
    Checks if a type is a parameterized generic (e.g., List[int]),
    returning True if it is, and False otherwise.
    """
    return get_origin(typ) is not None and bool(get_args(typ))


def custom_asdict_factory(data):
    """
    Custom factory function for converting a dataclass to a dictionary,
    with special handling
        * Enum types to value.
    """

    def convert_value(obj):
        match obj:
            case Enum():
                return obj.value
        return obj

    return dict((k, convert_value(v)) for k, v in data)


def get_first_non_none_type(union: UnionType) -> Type[Any]:
    """Return the first non None type from a UnionType, or None if not found."""
    return next((t for t in union.__args__ if t is not type(None)), type(None))


@dataclass(unsafe_hash=True)
class Dataclass:
    """
    A utility wrapper around the standard Python dataclass to
    extend the dataclass capabilities.

    This Dataclass support all the types supported by the Python dataclass.

    https://docs.python.org/3.10/library/dataclasses.html

    Additionally:
        *  support other Dataclass as fields.
        *  support multiple Dataclass inheritance.
        *  support field containing sequence of type SUPPORTED_DATACLASS_SEQUENCE_TYPES of other Dataclass.
        *  add from_dict() method to reconstruct the class from a dictionary, complete or partial.

    Methods:
        dataclass: Reference to the dataclass decorator.
        field: Reference to the dataclass field to as helper function to define fields with default values or other attributes.
        iter_fields: Iterate the defined dataclass fields
        from_dict: Reconstruct the class from a dictionary
        as_dict: Convert the class as dictionary

    """
    dataclass = dataclass
    field = field

    @classmethod
    def iter_fields(cls) -> Generator[Field, None, None]:
        """Return generator for iterating the Dataclass Field

        Returns:
            field:  dataclass component Field.
                    More info at https://docs.python.org/3.10/library/dataclasses.html#dataclasses.Field
        """
        for field in fields(cls):
            yield field

    @classmethod
    def from_dict(cls: Type[D], source_dict: dict) -> D:
        """
        Create an instance of the dataclass from a dictionary.
        This method iterate all the fields and recursively reconstruct
        all the Dataclass found in the way.

        Args:
            source_dict: The dictionary containing data to be converted to a dataclass instance.

        Returns:
            An instance of the Dataclass.

        Raises:
            ValueError: Wrong field name in source_dict that miss in the target cls Dataclass
        """
        # Retrieve all annotation, even looking in __mro__
        fields_types = get_type_hints(cls)

        # Check source_dict fields validity
        wrong_fields = set(source_dict.keys()) - set(fields_types.keys())
        if len(wrong_fields) > 0:
            raise ValueError(f"Unexpected fields found: {wrong_fields}")

        # Final reconstructed input dictionary
        reconstructed_dict = {}

        for field, field_value in source_dict.items():
            field_type = fields_types[field]
            is_optional_field = False
            # The field is optional
            if isinstance(field_type, UnionType):
                is_optional_field = True
                field_type = get_first_non_none_type(field_type)
            # The field is a Dataclass
            if issubclass(field_type, Dataclass):
                # Must be reconstructed from a dictionary
                # If it's an optional field also from None
                if not isinstance(field_value, dict) and not is_optional_field:
                    raise ValueError(
                        f"Found wrong field value type '{type(field_value)}' "
                        f"instead of '<class dict>' while reconstructing {field=}, {field_value=}"
                    )
                # Set None if the optional type passed is None
                # Instead call the recursive Dataclass construction if it's a dict
                reconstructed_value = None if (is_optional_field and field_value is None) else field_type.from_dict(field_value)
                reconstructed_dict[field] = reconstructed_value
            # The field is a parameterized_generic
            elif is_parameterized_generic(field_type):
                # Check if contains Dataclass
                sequence_type = get_sequence_element_type(field_type)
                if issubclass(sequence_type, Dataclass):
                    # The current supported Dataclass reconstruction on sequence are the following
                    orig_type = get_origin(field_type)
                    if orig_type not in SUPPORTED_DATACLASS_SEQUENCE_TYPES:
                        raise ValueError(
                            f"Unsupported sequence type '{orig_type}'."
                            f"Current supported Sequence for nested Dataclass are '{SUPPORTED_DATACLASS_SEQUENCE_TYPES}'"
                        )
                    reconstructed_dict[field] = field_type(sequence_type.from_dict(arg) for arg in field_value)
                # No reconstruction needed
                else:
                    reconstructed_dict[field] = field_value
            # No reconstruction needed
            else:
                reconstructed_value = None if (is_optional_field and field_value is None) else field_type(field_value)
                reconstructed_dict[field] = reconstructed_value

        return cls(**reconstructed_dict)

    def as_dict(self) -> dict:
        """
        Convert the dataclass instance to a dictionary.

        This method uses the `asdict` utility function from the `dataclasses` module
        to achieve the conversion. Nested dataclass instances, if any, will also
        be converted to dictionaries.

        Returns:
            A dictionary representation of the dataclass instance.
        """
        return asdict(self, dict_factory=custom_asdict_factory)

    def __setattr__(self, key, value):
        """
        Prevent attribute modifications if the object has is protected

        """
        if key != "_frozen" and getattr(self, "_frozen", False):
            raise AttributeError(f"Cannot modify {self.__class__.__name__} instance, it is 'frozen'")

        super().__setattr__(key, value)
