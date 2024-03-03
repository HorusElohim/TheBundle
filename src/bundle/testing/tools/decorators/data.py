from functools import wraps
from pathlib import Path
import jsonschema
import json

from .... import core
from .. import assertions, utils, TEST_LOGGER
from .cprofile import cprofile


def data(tmp_dir: Path, ref_dir: str | Path = None, cprofile_dump_dir: str | Path = None):

    ref_dir = utils.ensure_path(ref_dir)
    tmp_dir = utils.ensure_path(tmp_dir)
    cprofile_dir = utils.ensure_path(cprofile_dump_dir)

    @cprofile(cprofile_dump_dir=cprofile_dir)
    def test_pydantic_data_dict(class_instance: core.data.Data):
        assertions.instance_identity(class_instance, core.data.Data)
        class_instance_dict = class_instance.as_dict()
        new_class_instance = class_instance.from_dict(class_instance_dict)
        assertions.compare(new_class_instance, class_instance)
        return class_instance

    @cprofile(cprofile_dump_dir=cprofile_dir)
    def test_pydantic_data_json(class_instance: core.data.Data, tmp_dir: Path, ref_dir: Path):

        ref_json_path, tmp_json_path, failed_json_path, failed_error_log_path = utils.retrieves_tests_paths(
            "data/json", ref_dir, tmp_dir, class_instance, "pydantic_json"
        )

        try:
            class_instance.dump_json(tmp_json_path)
            new_instance = class_instance.from_json(tmp_json_path)
            assertions.compare(new_instance, class_instance)

            # Compare with stored ref exist
            if ref_json_path.exists():
                ref_instance = class_instance.from_json(ref_json_path)
                assertions.compare(ref_instance, class_instance)
            else:
                class_instance.dump_json(ref_json_path)
                TEST_LOGGER.debug(f"new ref has been saved {ref_json_path}")

        except Exception as ex:
            TEST_LOGGER.error(str(ex))
            failed_error_log_path.open("w").write(str(ex))
            class_instance.dump_json(failed_json_path)
            raise ex

        return class_instance

    @cprofile(cprofile_dump_dir=cprofile_dir)
    def test_pydantic_data_jsonschema(class_instance: core.data.Data, tmp_dir: Path, ref_dir: Path):

        ref_json_path, _, _, _ = utils.retrieves_tests_paths("data/json", ref_dir, tmp_dir, class_instance, "pydantic_json")

        ref_jsonschema_path, _, failed_jsonschema_path, failed_error_log_path = utils.retrieves_tests_paths(
            "data/jsonschema", ref_dir, tmp_dir, class_instance, "pydantic_jsonschema"
        )

        try:
            if not ref_json_path.exists():
                TEST_LOGGER.warning(f"jsonschema test skip because FileNotFound: {ref_json_path=}")
                return class_instance

            ref_dict = json.loads(ref_json_path.open("r").read())
            jsonschema.validate(instance=ref_dict, schema=class_instance.as_jsonschema())

            if not ref_jsonschema_path.exists():
                class_instance.dump_jsonschema(ref_jsonschema_path)

        except Exception as ex:
            TEST_LOGGER.error(str(ex))
            failed_error_log_path.open("w").write(str(ex))
            class_instance.dump_jsonschema(failed_jsonschema_path)
            raise ex

        return class_instance

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwds):
            class_instance = func(*args, **kwds)

            assertions.instance_identity(class_instance, core.data.Data)

            test_pydantic_data_dict(class_instance)

            test_pydantic_data_json(class_instance, tmp_dir, ref_dir)

            test_pydantic_data_jsonschema(class_instance, tmp_dir, ref_dir)

            return class_instance

        return wrapper

    return decorator
