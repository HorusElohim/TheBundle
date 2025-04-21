#pragma once
#include <memory>

namespace example_module::shape
{
    class Shape
    {
    public:
        virtual ~Shape() = default;
        virtual double area() const = 0;
    };
}
