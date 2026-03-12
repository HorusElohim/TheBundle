from bundle.pybind import Pybind
from bundle.tracy.pybind_plugin import TracyPlatformPlugin

Pybind.setup(__file__, plugins=[TracyPlatformPlugin()])
