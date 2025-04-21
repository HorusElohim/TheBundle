import sys
import subprocess
import shutil
import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def built_extension(tmp_path_factory):
    """
    Copy the real_case project into a temp directory, build via thebundle CLI,
    and prepend its bindings/python folder to sys.path for import.
    """
    # Source directory of this test
    src = Path(__file__).parent.resolve()
    dest = tmp_path_factory.mktemp("real_case")
    # Copy everything
    shutil.copytree(src, dest, dirs_exist_ok=True)

    # Run build via CLI: python -m bundle.pybind.cli build --path dest
    cmd = [
        "bundle",
        "pybind",
        "build",
        "--path", str(dest),
    ]
    subprocess.run(cmd, cwd=dest, check=True)

    # Prepend the python bindings directory
    bindings_dir = dest / "bindings" / "python"
    sys.path.insert(0, str(bindings_dir))
    yield dest


def test_free_function(built_extension):
    import realpkg.bindings as ext
    assert ext.add(2, 3) == 5


def test_adder_class(built_extension):
    from realpkg.bindings import Adder
    a = Adder(10)
    assert a.add(5) == 15
