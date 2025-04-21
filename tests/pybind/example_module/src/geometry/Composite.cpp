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
