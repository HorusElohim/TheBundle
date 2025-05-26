from bundle.pybind import Pybind

### Build C++ library before compiling the Python bindings
# This step is necessary to ensure that the C++ library is built before we attempt to compile the Python bindings.
# If you have installed the C++ library using CMake, it will be founded automatically by pkg-config.
#
# python build.py


Pybind.setup(__file__)
