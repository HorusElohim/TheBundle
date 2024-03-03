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

import difflib

from ...core.logger import get_logger

LOGGER = get_logger("bundle.testing")


def instance_identity(instance, class_type):
    """
    Validates that an instance belongs to a specified class or a subclass thereof.

    Asserts that the first argument is an instance and not a class, and that it
    is an instance of the specified class or its subclass.

    Args:
        instance: The object to check.
        class_type: The class to which the instance should belong.

    Raises:
        AssertionError: If `instance` is a class or not an instance of `class_type` or its subclasses.
    """
    assert not isinstance(instance, type), f"{instance} must be an Instance, not a Class"
    assert issubclass(type(instance), class_type), f"The class {type(instance)=} must be a subclass of {class_type=}"


def compare(ref: object, tmp: object) -> None:
    """
    Compares two objects for equality and generates a detailed string diff if they differ.

    Converts each object to a string and uses difflib to compare these string representations.
    If differences are found, an AssertionError is raised with a detailed diff.

    Args:
        ref: The reference object to compare.
        tmp: The temporary object to compare against the reference.

    Raises:
        AssertionError: If `ref` and `tmp` are not equal, with a detailed diff as the error message.
    """
    ref_str = str(ref)
    tmp_str = str(tmp)
    ref_lines = ref_str.split(" ")
    tmp_lines = tmp_str.split(" ")

    differ = difflib.Differ()
    diff = list(differ.compare(ref_lines, tmp_lines))

    diff_str = "\n".join(diff)
    assert (
        ref == tmp
    ), f"""

REF: {ref.__class__=}:
{ref}

--
TEST: {tmp.__class__=}:
{tmp}

--
DIFF:
{diff_str}
"""
