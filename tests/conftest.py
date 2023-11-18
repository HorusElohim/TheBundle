# tests/conftest.py
import pytest
import bundle
import platform


@pytest.fixture(scope="session")
def bundle_folder():
    return bundle.Path(bundle.__file__).parent.parent.parent.absolute()


@pytest.fixture(scope="session")
def reference_folder(bundle_folder):
    ref_folder = bundle_folder / "references" / platform.system().lower()
    ref_folder.mkdir(exist_ok=True, parents=True)
    return ref_folder


@pytest.fixture(scope="session")
def cprofile_folder(reference_folder):
    cprof_folder = reference_folder / "cprofile"
    cprof_folder.mkdir(exist_ok=True)
    return cprof_folder
