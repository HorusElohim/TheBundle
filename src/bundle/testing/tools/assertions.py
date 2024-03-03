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
import difflib

LOGGER = logging.getLogger(__name__)


def instance_identity(instance, class_type):
    assert not isinstance(instance, type), f"{instance} must be an Instance, not a Class"
    assert issubclass(type(instance), class_type), f"The class {type(instance)=} must be a subclass of {class_type=}"


def compare(ref: object, tmp: object) -> None:
    """Compare the content of two objects and generate a diff."""
    ref_str = str(ref)
    tmp_str = str(tmp)

    # Generate a list of lines for each string representation
    ref_lines = ref_str.split(" ")
    tmp_lines = tmp_str.split(" ")

    # Create a Differ object
    differ = difflib.Differ()

    # Compute the difference
    diff = list(differ.compare(ref_lines, tmp_lines))

    # Check if there are differences and assert accordingly
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
