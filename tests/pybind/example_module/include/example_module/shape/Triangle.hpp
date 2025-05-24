#pragma once
#include "example_module/shape/Shape.hpp"
#include <memory>

namespace example_module::shape
{
    class Triangle : public Shape
    {
    public:
        Triangle(double base, double height);
        double area() const override;

    private:
        double base_, height_;
    };

    std::shared_ptr<Triangle> create_triangle(double base, double height);
}
