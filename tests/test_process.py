import os
import pytest
import bundle

bundle.tests.LOGGER.debug("PROCESS_TESTS")


PROCESS_CLASSES_TO_TEST = [
    bundle.tests.TestProcess,
    bundle.tests.TestAsyncProcess,
    bundle.tests.TestStreamingProcess,
    bundle.tests.TestStreamingAsyncProcess,
]


@pytest.mark.parametrize("process_class", PROCESS_CLASSES_TO_TEST)
def test_process_initialization(reference_folder, cprofile_folder, process_class, tmp_path: bundle.Path):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def process_initialization_default():
        return process_class()

    process_initialization_default()


@pytest.mark.parametrize(
    "process_class, expected_stdout, expected_stderr",
    [
        (bundle.tests.TestProcess(command='printf "Test"'), "Test",  ""),
        (bundle.tests.TestAsyncProcess(command="printf AsyncTest"), "AsyncTest",  ""),
        (bundle.tests.TestStreamingProcess(command="printf StreamingTest"),"StreamingTest", "",),
        (bundle.tests.TestStreamingAsyncProcess(command="printf StreamingAsyncTest"),"StreamingAsyncTest", "",),
    ],
)
def test_process_execution(cprofile_folder, process_class, expected_stdout, expected_stderr):
    @bundle.tests.process_decorator(
        expected_stdout=expected_stdout,
        expected_stderr=expected_stderr,
        cprofile_dump_dir=cprofile_folder,
    )
    def process_execution():
        return process_class

    process_execution()
