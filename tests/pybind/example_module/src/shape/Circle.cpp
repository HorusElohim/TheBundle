#include "example_module/shape/Circle.hpp"
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace example_module::shape
{
    Circle::Circle(double r) : radius_(r) {}
    double Circle::area() const { return M_PI * radius_ * radius_; }

    std::shared_ptr<Circle> create_circle(double r)
    {
        return std::make_shared<Circle>(r);
    }
}
