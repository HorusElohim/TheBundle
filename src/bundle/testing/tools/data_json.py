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
from pathlib import Path
from functools import wraps

from ... import data
from . import assert_instance_identity, assert_compare

LOGGER = logging.getLogger(__name__)


@data.dataclass
class InnerDatajson(data.json.JSONData):
    json_str: str = ""
    int_value: int = 1
    float_value: float = 1.0


@data.dataclass
class NestedDatajson(data.json.JSONData):
    nested: InnerDatajson = data.field(default_factory=InnerDatajson)


def json_decorator(tmp: Path, ref_dir: str | Path = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwds):
            class_instance = func(*args, **kwds)
            assert_instance_identity(class_instance, data.json.JSONData)

            filename = f"{type(class_instance).__name__}.json"

            ref_json_path = ref_dir / "ref" / filename
            schema_json_path = ref_dir / "schema" / filename
            stored_json_path = ref_dir / "ref" / filename
            failed_json_path = ref_dir / "failed" / filename
            failed_error_path = ref_dir / "failed" / "logs" / filename
            tmp_path = Path(tmp)

            ref_json_path.parent.mkdir(exist_ok=True)
            schema_json_path.parent.mkdir(exist_ok=True)
            stored_json_path.parent.mkdir(exist_ok=True)
            failed_json_path.parent.mkdir(exist_ok=True)
            failed_error_path.parent.mkdir(exist_ok=True)
            tmp_path.mkdir(exist_ok=True)

            # Self to json
            tmp_json_path = tmp_path / filename
            class_instance.dump_json(tmp_json_path)

            # New self from json
            new_instance = class_instance.from_json(tmp_json_path)
            save_ref = True

            try:
                # Compare with new self class_instance
                assert_compare(new_instance, class_instance)

                # Compare with stored ref exist
                if ref_json_path.exists():
                    ref_instance = class_instance.from_json(ref_json_path)
                    assert_compare(ref_instance, class_instance)
                    save_ref = False
                    # Compare with stored schema
                    if schema_json_path.exists():
                        class_instance.is_valid_by_jsonschema(ref_json_path)

            except Exception as ex:
                LOGGER.error(str(ex))
                failed_error_path.open("w").write(str(ex))
                class_instance.dump_json(failed_json_path)
                raise ex
            finally:
                if save_ref:
                    class_instance.dump_json(ref_json_path)
                    LOGGER.info(f"new ref has been saved {ref_json_path}")
                class_instance.to_jsonschema(schema_json_path)

            return class_instance

        return wrapper

    return decorator
