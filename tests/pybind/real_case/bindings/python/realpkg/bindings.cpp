#include <pybind11/pybind11.h>
#include "adder.hpp"

namespace py = pybind11;

PYBIND11_MODULE(bindings, m) {
    m.doc() = "Real case pybind11 extension";

    m.def("add", &add, "Add two integers");

    py::class_<Adder>(m, "Adder")
        .def(py::init<int>())
        .def("add", &Adder::add);
}
