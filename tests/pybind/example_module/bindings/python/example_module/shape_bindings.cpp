// Copyright 2026 HorusElohim
//
// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

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
