import pytest
import bundle

bundle.tests.LOGGER.debug("DATA_TESTS")

DATA_CLASSES_TO_TEST = [
    bundle.data.Dataclass,
    bundle.tests.OverrideDataclass,
    bundle.tests.NestedDataclass,
]


@pytest.mark.parametrize("dataclass", DATA_CLASSES_TO_TEST)
def test_dataclass(cprofile_folder, dataclass):
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def dataclass_default_init():
        return dataclass()

    dataclass_default_init()


JSONDATA_CLASSES_TO_TEST = [
    bundle.data.JSONData,
    bundle.tests.NestedDatajson,
]


@pytest.mark.parametrize("datajson", JSONDATA_CLASSES_TO_TEST)
def test_dataclass_json(cprofile_folder, reference_folder, datajson, tmp_path: bundle.Path):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def dataclass_json_default_init():
        return datajson()

    dataclass_json_default_init()
