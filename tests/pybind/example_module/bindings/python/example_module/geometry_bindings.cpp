#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "example_module/geometry/Utils.hpp"
#include "example_module/geometry/Composite.hpp"
#include "example_module/geometry/Utils.hpp"
#include "example_module/shape/Shape.hpp" // for shared_ptr<Shape>

namespace py = pybind11;
using namespace example_module::geometry;
using namespace example_module::shape;

PYBIND11_MODULE(geometry, m)
{
    m.doc() = "Geometry submodule";

    m.def("wrap_shapes", &wrap_shapes, py::arg("shapes"));

    m.def("maybe_make_circle", &maybe_make_circle, py::arg("flag"));
    m.def("maybe_make_square", &maybe_make_square, py::arg("flag"));
    m.def("maybe_make_triangle", &maybe_make_triangle, py::arg("flag"));

    m.def("get_shape_variant", &get_shape_variant, py::arg("flag"));

    py::class_<CompositeShape, Shape, std::shared_ptr<CompositeShape>>(m, "CompositeShape")
        .def(py::init<>())
        .def("add", &CompositeShape::add)
        .def("area", &CompositeShape::area);

    m.def("make_composite", &make_composite);
}
