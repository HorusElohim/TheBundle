#include "example_module/geometry/Utils.hpp"

namespace example_module::geometry
{
    double wrap_shapes(const std::vector<std::shared_ptr<shape::Shape>> &shapes)
    {
        double sum = 0;
        for (auto &s : shapes)
            sum += s->area();
        return sum;
    }
    std::optional<std::shared_ptr<shape::Circle>> maybe_make_circle(bool flag)
    {
        if (flag)
        {
            return std::make_shared<shape::Circle>(1.1);
        }
        else
        {
            return std::nullopt;
        }
    }
    std::optional<std::shared_ptr<shape::Square>> maybe_make_square(bool flag)
    {
        if (flag)
        {
            return std::make_shared<shape::Square>(2.2);
        }
        else
        {
            return std::nullopt;
        }
    }
    std::optional<std::shared_ptr<shape::Triangle>> maybe_make_triangle(bool flag)
    {
        if (flag)
        {
            return std::make_shared<shape::Triangle>(3.3, 4.4);
        }
        else
        {
            return std::nullopt;
        }
    }
    ShapeVariant get_shape_variant(bool flag)
    {
        if (flag)
            return std::make_shared<shape::Circle>(5.0);
        return std::make_shared<shape::Square>(6.0);
    }
}
