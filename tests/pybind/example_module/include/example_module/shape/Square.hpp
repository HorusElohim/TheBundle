#pragma once
#include "example_module/shape/Shape.hpp"
#include <memory>

namespace example_module::shape
{
    class Square : public Shape
    {
    public:
        explicit Square(double side);
        double area() const override;

    private:
        double side_;
    };

    std::shared_ptr<Square> create_square(double side);
}
