import os
import pytest
import bundle

bundle.tests.LOGGER.debug("PROCESS_TESTS")

def normalize_line_endings(s):
    return s.replace(os.linesep, '\n')

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
        (bundle.tests.TestProcess(command='echo "Test"'), "Test\n", ""),
        # (bundle.tests.TestAsyncProcess(command="echo AsyncTest"), "AsyncTest\n", ""),
        # (bundle.tests.TestStreamingProcess(command="echo StreamingTest"),"StreamingTest\n","",),
        # (bundle.tests.TestStreamingAsyncProcess(command="echo StreamingAsyncTest"),"StreamingAsyncTest\n","",),
    ],
)
def test_process_execution(cprofile_folder, process_class, expected_stdout, expected_stderr):
    @bundle.tests.process_decorator(
        expected_stdout=normalize_line_endings(expected_stdout),
        expected_stderr=normalize_line_endings(expected_stderr),
        cprofile_dump_dir=cprofile_folder,
    )
    def process_execution():
        return process_class

    process_execution()
