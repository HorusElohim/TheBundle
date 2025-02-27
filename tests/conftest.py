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

import pytest
import bundle
import platform
import shutil
import tempfile

logger = bundle.core.logger.get_logger(__name__)

bundle.BUNDLE_LOGGER.setLevel(bundle.core.logger.Level.TESTING)

# Avoid show expected exception
bundle.core.tracer.DEFAULT_LOG_EXC_LEVEL = bundle.core.logger.Level.EXPECTED_EXCEPTION

logger.parent = bundle.BUNDLE_LOGGER

logger.testing("Loading conftest.py")


def _get_bundle_folder():
    """Returns the absolute path to the bundle's root folder."""
    return bundle.Path(bundle.__file__).parent.parent.parent.absolute()


def _get_reference_folder(bundle_folder: bundle.Path):
    """
    Returns the path to the reference folder for the current platform,
    creating it if necessary.
    """
    ref_folder = bundle_folder / "references" / platform.system().lower()
    ref_folder.mkdir(exist_ok=True, parents=True)
    return ref_folder


def _get_cprofile_folder(reference_folder: bundle.Path):
    """
    Returns the path to the cprofile folder within the reference folder,
    creating it if necessary.
    """
    cprof_folder = reference_folder / "cprofile"
    cprof_folder.mkdir(exist_ok=True)
    return cprof_folder


@pytest.fixture(scope="session")
def bundle_folder():
    """Returns the absolute path to the bundle's root folder."""
    return _get_bundle_folder()


@pytest.fixture(scope="session")
def reference_folder(bundle_folder):
    """
    Returns the path to the reference folder for the current platform,
    creating it if necessary.
    """
    return _get_reference_folder(bundle_folder)


@pytest.fixture(scope="session")
def cprofile_folder(reference_folder):
    """
    Returns the path to the cprofile folder within the reference folder,
    creating it if necessary.
    """
    return _get_cprofile_folder(reference_folder)


@pytest.fixture(scope="session")
def assets_folder(bundle_folder):
    """Returns the path to the assets folder within the bundle's testing directory."""
    return bundle_folder / "src" / "bundle" / "testing" / "assets"


@pytest.fixture(scope="session", autouse=True)
def trace_test_suite():
    """Start and end the Tracy frame mark for the entire test session."""
    import tracy_client

    tracy_client.frame_mark()


def pytest_configure(config):
    # CPROFILE
    config.addinivalue_line(
        "markers",
        "bundle_cprofile(expected_duration=0, performance_threshold=10000000, cprofile_folder): Apply cprofile decorator with specified parameters",
    )
    # DATA
    config.addinivalue_line(
        "markers",
        "bundle_data(ref_dir=None, tmp_dir=None, cprofile_folder=None): Apply data decorator with specified parameters",
    )


def pytest_collection_modifyitems(session, config, items):
    # Compute bundle_folder
    bundle_folder = _get_bundle_folder()

    # Compute reference_folder
    reference_folder = _get_reference_folder(bundle_folder)

    # Compute cprofile_folder
    cprofile_folder = _get_cprofile_folder(reference_folder)

    # Initialize a list to store temp dirs for cleanup
    if not hasattr(session, "collected_temp_dirs"):
        session.collected_temp_dirs = []

    for item in items:
        # Bundle cprofile marker
        if cprofile_marker := item.get_closest_marker("bundle_cprofile"):
            logger.testing(f"added @cprofile marker to {item.name}")
            expected_duration = cprofile_marker.kwargs.get("expected_duration", 0)
            performance_threshold = cprofile_marker.kwargs.get("performance_threshold", 10_000_000)  # Default 10 ms

            original_func = item.obj

            # Apply the cprofile_decorator with parameters, excluding cprofile_folder
            decorated_func = bundle.testing.decorators.cprofile(
                expected_duration=expected_duration,
                performance_threshold=performance_threshold,
                cprofile_folder=cprofile_folder,
            )(original_func)

            # Replace the test function with the decorated one
            item.obj = decorated_func

        # Bundle data marker
        if data_marker := item.get_closest_marker("bundle_data"):
            logger.testing(f"added @data marker to {item.name}")
            ref_dir = data_marker.kwargs.get("ref_dir", str(reference_folder))
            # Create a temporary directory for data decoration
            tmp_dir = bundle.Path(tempfile.mkdtemp(prefix=f"data_{item.name}"))
            session.collected_temp_dirs.append(tmp_dir)

            cprofile_dir = data_marker.kwargs.get("cprofile_folder", str(cprofile_folder))

            # Apply the data_decorator with parameters
            decorated_func = bundle.testing.decorators.data(
                ref_dir=ref_dir,
                tmp_dir=tmp_dir,
                cprofile_folder=cprofile_dir,
            )(item.obj)

            # Replace the test function with the decorated one
            item.obj = decorated_func


def pytest_sessionfinish(session, exitstatus):
    # Cleanup all temp dirs
    logger.testing("Cleaning up temporary directories.")
    temp_dirs = getattr(session, "collected_temp_dirs", [])
    for temp_dir in temp_dirs:
        try:
            shutil.rmtree(temp_dir)
            logger.testing(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Failed to delete temporary directory {temp_dir}: {e}")
