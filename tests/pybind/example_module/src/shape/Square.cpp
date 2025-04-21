#include "example_module/shape/Square.hpp"

namespace example_module::shape
{
    Square::Square(double s) : side_(s) {}
    double Square::area() const { return side_ * side_; }

    std::shared_ptr<Square> create_square(double s)
    {
        return std::make_shared<Square>(s);
    }
}
