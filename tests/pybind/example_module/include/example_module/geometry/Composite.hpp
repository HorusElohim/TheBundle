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
