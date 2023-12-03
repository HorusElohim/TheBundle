import pytest
import bundle
from bundle import testing

bundle.tests.LOGGER.debug("TASK_TESTS")

GRAPH_CLASSES_TO_TEST = [
    testing.TestGraph.Sync,
    testing.TestGraph.Async,
]


@pytest.mark.parametrize("graph", GRAPH_CLASSES_TO_TEST)
def test_graph_initialization(graph: type(bundle.Graph.Abc), tmp_path, reference_folder, cprofile_folder):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def graph_initialization_default():
        return graph()

    graph_initialization_default()


ROOT_NODE_TO_TEST = testing.TestGraph.TestNodeSync(
    name="RootNode",
    children=[
        testing.TestGraph.TestNodeSync(
            name="ChildNode1",
            children=[
                testing.TestGraph.TestNodeSync(name="ChildNode1Child1"),
                testing.TestGraph.TestNodeAsync(
                    name="ChildNode1Child2",
                    children=[
                        testing.TestGraph.TestNodeSync(name="ChildNode1Child2Child1"),
                        testing.TestGraph.TestNodeAsync(name="ChildNode1Child2Child2"),
                    ],
                ),
            ],
        ),
        testing.TestGraph.TestNodeAsync(
            name="ChildNode2",
            children=[
                testing.TestGraph.TestNodeSync(name="ChildNode2Child1"),
                testing.TestGraph.TestNodeAsync(
                    name="ChildNode2Child2",
                    children=[
                        testing.TestGraph.TestNodeSync(name="ChildNode1Child1Child1"),
                        testing.TestGraph.TestNodeAsync(name="ChildNode1Child2Child2"),
                    ],
                ),
            ],
        ),
    ],
)


@pytest.mark.parametrize(
    "graph",
    [
        testing.TestGraph.Sync(name="GraphTask", root=ROOT_NODE_TO_TEST),
        testing.TestGraph.Async(name="GraphAsyncTask", root=ROOT_NODE_TO_TEST),
    ],
)
def test_graph_execution(cprofile_folder, reference_folder, graph: bundle.Graph.Abc):
    @bundle.tests.graph_decorator(reference_folder, cprofile_folder)
    def graph_execution():
        return graph

    graph_execution()
