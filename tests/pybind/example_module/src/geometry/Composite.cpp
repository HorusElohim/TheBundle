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

#include "example_module/geometry/Composite.hpp"

namespace example_module::geometry
{
    void CompositeShape::add(std::shared_ptr<shape::Shape> s)
    {
        children_.push_back(std::move(s));
    }
    double CompositeShape::area() const
    {
        double sum = 0;
        for (auto &c : children_)
            sum += c->area();
        return sum;
    }
    std::shared_ptr<CompositeShape> make_composite()
    {
        return std::make_shared<CompositeShape>();
    }
}
