import pytest
import bundle

bundle.tests.LOGGER.debug("TASK_TESTS")

NODES_CLASSES_TO_TEST = [
    bundle.tests.TestNodeTask,
    bundle.tests.TestNodeProcess,
    bundle.tests.TestNodeAsyncTask,
    bundle.tests.TestNodeAsyncProcess,
]


@pytest.mark.parametrize("node", NODES_CLASSES_TO_TEST)
def test_node_initialization(node, tmp_path, reference_folder, cprofile_folder):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def node_initialization_default():
        return node()

    node_initialization_default()


@pytest.mark.parametrize(
    "node, result",
    [
        (bundle.tests.TestTask(name="Node"), "Node"),
        (bundle.tests.TestAsyncTask(name="NodeAsyncTask"), "NodeAsyncTask"),
    ],
)
def test_node_task_execution(cprofile_folder, node, result):
    @bundle.tests.task_decorator(expected_result=result, cprofile_dump_dir=cprofile_folder)
    def node_task_execution():
        return node

    node_task_execution()


@pytest.mark.parametrize(
    "node, expected_stdout, expected_stderr",
    [
        (bundle.tests.TestNodeProcess(command='printf "Test"'), "Test", ""),
        (bundle.tests.TestNodeAsyncProcess(command="printf AsyncTest"), "AsyncTest", ""),
        (bundle.tests.TestNodeStreamingProcess(command="printf StreamingTest"),"StreamingTest", "",),
        (bundle.tests.TestNodeStreamingAsyncProcess(command="printf StreamingAsyncTest"),"StreamingAsyncTest", "",),
    ],
)
def test_process_execution(cprofile_folder, node, expected_stdout, expected_stderr):
    @bundle.tests.process_decorator(
        expected_stdout=expected_stdout,
        expected_stderr=expected_stderr,
        cprofile_dump_dir=cprofile_folder,
    )
    def node_process_execution():
        return node

    node_process_execution()
