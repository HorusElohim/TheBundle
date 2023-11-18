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


from functools import wraps

from ... import data
from . import assert_instance_identity, assert_compare


@data.dataclass
class OverrideDataclass(data.Dataclass):
    I: int = 1
    name: str = __name__
    version: float = 1.0


@data.dataclass
class NestedDataclass(data.Dataclass):
    nested: OverrideDataclass = data.Dataclass.field(default_factory=OverrideDataclass)


def data_decorator(*data_args, **data_kwargs):
    def decorator(func):
        @wraps(func)
        def wrapper(*func_args, **func_kwds):
            class_instance = func(*func_args, **func_kwds)
            assert_instance_identity(class_instance, data.Dataclass)
            class_instance_dict = class_instance.as_dict()
            new_class_instance = class_instance.from_dict(class_instance_dict)
            assert_compare(new_class_instance, class_instance)
            return class_instance

        return wrapper

    return decorator
