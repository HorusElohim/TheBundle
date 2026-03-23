# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

from bundle.core import data

from ..base import GraphicBaseComponent, GraphicComponentParams


class GraphicTwoDComponentParams(GraphicComponentParams):
    """Shared parameters for 2D graphics components."""

    render_mode: str = "2d"
    width: int | None = None
    height: int | None = None
    device_pixel_ratio_cap: float = 2.0

    @data.field_validator("device_pixel_ratio_cap")
    @classmethod
    def _validate_ratio_cap(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("device_pixel_ratio_cap must be greater than 0")
        return value


class GraphicTwoDComponent(GraphicBaseComponent):
    """Base class for canvas/SVG style 2D graphics components."""

    params: GraphicTwoDComponentParams = data.Field(
        default_factory=GraphicTwoDComponentParams
    )
