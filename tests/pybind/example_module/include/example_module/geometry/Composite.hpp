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

#pragma once
#include "example_module/shape/Shape.hpp"
#include <memory>
#include <vector>

namespace example_module::geometry
{
    class CompositeShape : public shape::Shape
    {
    public:
        CompositeShape() = default;
        void add(std::shared_ptr<shape::Shape> s);
        double area() const override;

    private:
        std::vector<std::shared_ptr<shape::Shape>> children_;
    };

    std::shared_ptr<CompositeShape> make_composite();
}
