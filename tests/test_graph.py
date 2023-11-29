import pytest
import bundle

bundle.tests.LOGGER.debug("TASK_TESTS")

GRAPH_CLASSES_TO_TEST = [
    bundle.tests.TestGraphTask,
    bundle.tests.TestGraphAsyncTask,
]


@pytest.mark.parametrize("graph", GRAPH_CLASSES_TO_TEST)
def test_graph_initialization(graph: type(bundle.graphs.GraphABC), tmp_path, reference_folder, cprofile_folder):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def graph_initialization_default():
        return graph()

    graph_initialization_default()


ROOT_NODE_TO_TEST = bundle.tests.TestGraphNodeTask(
    name="RootNode",
    children=[
        bundle.tests.TestGraphNodeTask(
            name="ChildNode1",
            children=[
                bundle.tests.TestGraphNodeTask(name="ChildNode1Child1"),
                bundle.tests.TestGraphNodeAsyncTask(
                    name="ChildNode1Child2",
                    children=[
                        bundle.tests.TestGraphNodeTask(name="ChildNode1Child2Child1"),
                        bundle.tests.TestGraphNodeAsyncTask(name="ChildNode1Child2Child2"),
                    ],
                ),
            ],
        ),
        bundle.tests.TestGraphNodeAsyncTask(
            name="ChildNode2",
            children=[
                bundle.tests.TestGraphNodeTask(name="ChildNode2Child1"),
                bundle.tests.TestGraphNodeAsyncTask(
                    name="ChildNode2Child2",
                    children=[
                        bundle.tests.TestGraphNodeTask(name="ChildNode1Child1Child1"),
                        bundle.tests.TestGraphNodeAsyncTask(name="ChildNode1Child2Child2"),
                    ],
                ),
            ],
        ),
    ],
)


@pytest.mark.parametrize(
    "graph",
    [
        bundle.tests.TestGraphTask(name="GraphTask", root=ROOT_NODE_TO_TEST),
        bundle.tests.TestGraphAsyncTask(name="GraphAsyncTask", root=ROOT_NODE_TO_TEST),
    ],
)
def test_graph_execution(cprofile_folder, reference_folder, graph: bundle.graphs.GraphABC):
    @bundle.tests.graph_decorator(reference_folder, cprofile_folder)
    def graph_execution():
        return graph

    graph_execution()
