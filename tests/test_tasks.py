import pytest
import bundle
from bundle.testing import TestTask

bundle.tests.LOGGER.debug("TASK_TESTS")

TASK_CLASSES_TO_TEST = [
    TestTask.Sync,
    TestTask.Async,
]


@pytest.mark.parametrize("task", TASK_CLASSES_TO_TEST)
def test_task_initialization(task, tmp_path, reference_folder, cprofile_folder):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def task_initialization_default():
        return task()

    task_initialization_default()


@pytest.mark.parametrize(
    "task, result",
    [
        (TestTask.Sync(name="Task"), "Task"),
        (TestTask.Async(name="AsyncTask"), "AsyncTask"),
    ],
)
def test_task_execution(cprofile_folder, task, result):
    @bundle.tests.task_decorator(expected_result=result, cprofile_dump_dir=cprofile_folder)
    def task_execution():
        return task

    task_execution()
