#include "example_module/shape/Triangle.hpp"

namespace example_module::shape
{
    Triangle::Triangle(double b, double h) : base_(b), height_(h) {}
    double Triangle::area() const { return 0.5 * base_ * height_; }

    std::shared_ptr<Triangle> create_triangle(double b, double h)
    {
        return std::make_shared<Triangle>(b, h);
    }
}
