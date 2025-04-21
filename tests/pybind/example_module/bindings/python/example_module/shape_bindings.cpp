#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "example_module/shape/Shape.hpp"
#include "example_module/shape/Circle.hpp"
#include "example_module/shape/Square.hpp"
#include "example_module/shape/Triangle.hpp"

namespace py = pybind11;
using namespace example_module::shape;

PYBIND11_MODULE(shape, m)
{
    m.doc() = "Shape submodule";

    py::class_<Shape, std::shared_ptr<Shape>>(m, "Shape")
        .def("area", &Shape::area);

    py::class_<Circle, Shape, std::shared_ptr<Circle>>(m, "Circle")
        .def(py::init<double>(), py::arg("radius"))
        .def("area", &Circle::area);

    py::class_<Square, Shape, std::shared_ptr<Square>>(m, "Square")
        .def(py::init<double>(), py::arg("side"))
        .def("area", &Square::area);

    py::class_<Triangle, Shape, std::shared_ptr<Triangle>>(m, "Triangle")
        .def(py::init<double, double>(), py::arg("base"), py::arg("height"))
        .def("area", &Triangle::area);
}
