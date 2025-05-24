#pragma once

#include "example_module/shape/Circle.hpp"
#include "example_module/shape/Shape.hpp"
#include "example_module/shape/Square.hpp"
#include "example_module/shape/Triangle.hpp"

#include <memory>
#include <optional>
#include <vector>

#if __cplusplus >= 201703L && (!defined(__APPLE__) || (defined(__APPLE__) && defined(__MAC_OS_X_VERSION_MIN_REQUIRED) && __MAC_OS_X_VERSION_MIN_REQUIRED >= 101300))
#include <variant>
using ShapeVariant = std::variant<
    std::shared_ptr<example_module::shape::Circle>,
    std::shared_ptr<example_module::shape::Square>,
    std::shared_ptr<example_module::shape::Triangle>>;
#endif

namespace example_module::geometry
{
    double wrap_shapes(const std::vector<std::shared_ptr<shape::Shape>> &shapes);

    std::optional<std::shared_ptr<shape::Circle>> maybe_make_circle(bool flag);
    std::optional<std::shared_ptr<shape::Square>> maybe_make_square(bool flag);
    std::optional<std::shared_ptr<shape::Triangle>> maybe_make_triangle(bool flag);

#if __cplusplus >= 201703L && (!defined(__APPLE__) || (defined(__APPLE__) && defined(__MAC_OS_X_VERSION_MIN_REQUIRED) && __MAC_OS_X_VERSION_MIN_REQUIRED >= 101300))
    ShapeVariant get_shape_variant(bool flag);
#endif
}
