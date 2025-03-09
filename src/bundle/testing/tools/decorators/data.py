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

import json
from functools import wraps
from pathlib import Path

import jsonschema

from .... import core
from .. import assertions, utils
from .cprofile import cprofile

logger = core.logger.get_logger("bundle.testing")


def data(tmp_dir: Path, ref_dir: str | Path, cprofile_folder: str | Path):
    """
    Decorator for testing bundle Data model serialization and schema validation.

    Wraps test functions to perform round-trip dict and JSON serialization tests,
    and validates the model against its JSON schema. Tests are profiled using cprofile.
    Results and errors are logged, with provision for updating reference data.

    Args:
        tmp_dir (Path): Temporary directory for test outputs.
        ref_dir (str | Path): Reference directory for baseline data.
        cprofile_folder (str | Path): Directory for cprofile output.

    Returns:
        Decorator: A decorator that wraps test functions to extend their functionality
                   with serialization and validation tests.
    """
    ref_dir = utils.ensure_path(ref_dir)
    tmp_dir = utils.ensure_path(tmp_dir)
    cprofile_dir = utils.ensure_path(cprofile_folder)

    @cprofile(cprofile_folder=cprofile_dir)
    @core.tracer.Async.decorator.call_raise(log_level=core.logger.Level.TESTING)
    async def test_pydantic_data_as_dict(class_instance: core.Data):
        logger.testing(f"test_pydantic_data_as_dict: {utils.class_instance_name(class_instance)}")
        return class_instance, await class_instance.as_dict()

    @cprofile(cprofile_folder=cprofile_dir)
    @core.tracer.Async.decorator.call_raise(log_level=core.logger.Level.TESTING)
    async def test_pydantic_data_from_dict(class_instance: core.Data, class_instance_dict: dict):
        logger.testing(f"test_pydantic_data_from_dict: {utils.class_instance_name(class_instance)}")
        return class_instance, await class_instance.from_dict(class_instance_dict)

    @cprofile(cprofile_folder=cprofile_dir)
    @core.tracer.Async.decorator.call_raise(log_level=core.logger.Level.TESTING)
    async def test_pydantic_data_compare(class_instance: core.Data, class_instance_from_dict: core.Data):
        logger.testing(f"test_pydantic_data_compare: {utils.class_instance_name(class_instance)}")
        assertions.compare(class_instance_from_dict, class_instance)
        return class_instance

    @cprofile(cprofile_folder=cprofile_dir)
    @core.tracer.Async.decorator.call_raise(log_level=core.logger.Level.TESTING)
    async def test_pydantic_data_as_json(
        class_instance: core.Data, tmp_json_path: Path, failed_json_path: Path, failed_error_log_path: Path
    ):
        logger.testing(f"test_pydantic_data_as_json: {utils.class_instance_name(class_instance)}")
        try:
            await class_instance.as_json()
            return class_instance
        except Exception as ex:
            logger.error(str(ex))
            failed_error_log_path.open("a+").write("test_pydantic_data_as_json\n\n" + str(ex))
            await class_instance.dump_json(failed_json_path)
            raise ex

    @cprofile(cprofile_folder=cprofile_dir)
    @core.tracer.Async.decorator.call_raise(log_level=core.logger.Level.TESTING)
    async def test_pydantic_data_dump_json(
        class_instance: core.Data, tmp_json_path: Path, failed_json_path: Path, failed_error_log_path: Path
    ):
        logger.testing(f"test_pydantic_data_dump_json: {utils.class_instance_name(class_instance)}")
        try:
            await class_instance.dump_json(tmp_json_path)
            return class_instance
        except Exception as ex:
            logger.error(str(ex))
            failed_error_log_path.open("a+").write("test_pydantic_data_dump_json\n\n" + str(ex))
            await class_instance.dump_json(failed_json_path)
            raise ex

    @cprofile(cprofile_folder=cprofile_dir)
    @core.tracer.Async.decorator.call_raise(log_level=core.logger.Level.TESTING)
    async def test_pydantic_data_from_json(
        class_instance: core.Data, ref_json_path: Path, failed_json_path: Path, failed_error_log_path: Path
    ):
        logger.testing(f"test_pydantic_data_from_json: {utils.class_instance_name(class_instance)}")
        try:
            return class_instance, await class_instance.from_json(ref_json_path)
        except Exception as ex:
            logger.error(str(ex))
            failed_error_log_path.open("a+").write("test_pydantic_data_from_json\n\n" + str(ex))
            await class_instance.dump_json(failed_json_path)
            raise ex

    @cprofile(cprofile_folder=cprofile_dir)
    @core.tracer.Async.decorator.call_raise(log_level=core.logger.Level.TESTING)
    async def test_pydantic_data_dump_jsonschema(class_instance: core.Data, ref_jsonschema_path: Path):
        logger.testing(f"test_pydantic_data_dump_jsonschema: {utils.class_instance_name(class_instance)}")
        await class_instance.dump_jsonschema(ref_jsonschema_path)
        return class_instance

    @cprofile(cprofile_folder=cprofile_dir)
    @core.tracer.Async.decorator.call_raise(log_level=core.logger.Level.TESTING)
    async def test_pydantic_data_validate_dict_with_jsonschema(
        class_instance: core.Data,
        data_dict: dict,
        jsonschema_dict: dict,
        failed_error_log_path: Path,
        failed_jsonschema_path: Path,
    ):
        logger.testing(f"test_pydantic_data_validate_dict_with_jsonschema: {utils.class_instance_name(class_instance)}")
        try:
            jsonschema.validate(instance=data_dict, schema=jsonschema_dict)
            return class_instance
        except Exception as ex:
            logger.error(str(ex))
            failed_error_log_path.write_text(str(ex))
            await class_instance.dump_jsonschema(failed_jsonschema_path)
            raise ex

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwds):
            class_instance = await func(*args, **kwds)
            logger.testing(f"@data testing -> {utils.class_instance_name(class_instance)}")

            assertions.instance_identity(class_instance, core.Data)

            _, class_instance_dict = await test_pydantic_data_as_dict(class_instance)

            _, class_instance_from_dict = await test_pydantic_data_from_dict(class_instance, class_instance_dict)

            await test_pydantic_data_compare(class_instance, class_instance_from_dict)

            # Json tests path
            ref_json_path, tmp_json_path, failed_json_path, failed_error_log_path = utils.retrieves_tests_paths(
                "data/json", ref_dir, tmp_dir, class_instance, "pydantic_json"
            )

            await test_pydantic_data_as_json(class_instance, tmp_json_path, failed_json_path, failed_error_log_path)

            await test_pydantic_data_dump_json(class_instance, tmp_json_path, failed_json_path, failed_error_log_path)

            # Generate ref only if doesn't exists
            if not ref_json_path.exists():
                logger.verbose(f"json reference will be created {str(ref_json_path)}")
                ref_json_path.write_text(tmp_json_path.read_text())

            _, class_instance_from_json = await test_pydantic_data_from_json(
                class_instance, ref_json_path, failed_error_log_path, failed_error_log_path
            )

            await test_pydantic_data_compare(class_instance, class_instance_from_json)

            # Jsonschema tests path
            ref_jsonschema_path, _, failed_jsonschema_path, failed_error_log_path = utils.retrieves_tests_paths(
                "data/jsonschema", ref_dir, tmp_dir, class_instance, "pydantic_jsonschema"
            )

            # Generate jsonchema ref only if doesn't exists
            if not ref_jsonschema_path.exists():
                logger.verbose(f"jsonschema reference will be created {str(ref_json_path)}")
                await test_pydantic_data_dump_jsonschema(class_instance, ref_jsonschema_path)

            jsonschema_dict = await class_instance.as_jsonschema()

            ref_dict = json.loads(ref_json_path.open("r").read())

            await test_pydantic_data_validate_dict_with_jsonschema(
                class_instance,
                ref_dict,
                jsonschema_dict,
                failed_error_log_path,
                failed_jsonschema_path,
            )

            return class_instance

        return wrapper

    return decorator
