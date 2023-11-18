import bundle
import pytest

bundle.tests.LOGGER.debug("ENTITY_TESTS")

ENTITY_CLASSES_TO_TEST = [
    bundle.tests.TestEntity,
]


@pytest.mark.parametrize("entity", ENTITY_CLASSES_TO_TEST)
def test_entity(reference_folder, cprofile_folder, entity, tmp_path: bundle.Path):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def entity_default_init():
        return entity()

    entity_default_init()
