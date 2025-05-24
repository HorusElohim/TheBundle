#pragma once
#include "example_module/shape/Shape.hpp"
#include <memory>

namespace example_module::shape
{
    class Circle : public Shape
    {
    public:
        explicit Circle(double radius);
        double area() const override;

    private:
        double radius_;
    };

    std::shared_ptr<Circle> create_circle(double radius);
}
