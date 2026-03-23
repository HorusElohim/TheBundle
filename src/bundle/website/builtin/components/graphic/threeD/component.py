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


class GraphicThreeDComponentParams(GraphicComponentParams):
    """Shared parameters for 3D graphics components."""

    render_mode: str = "3d"
    camera_mode: str = "orbit"
    field_of_view: float = 40.0
    near: float = 0.1
    far: float = 100.0

    @data.model_validator(mode="after")
    def _validate_camera_clip(self):
        if self.field_of_view <= 0:
            raise ValueError("field_of_view must be greater than 0")
        if self.near <= 0:
            raise ValueError("near clip distance must be greater than 0")
        if self.far <= self.near:
            raise ValueError("far clip distance must be greater than near clip distance")
        return self


class GraphicThreeDComponent(GraphicBaseComponent):
    """Base class for Three.js/WebGL style 3D graphics components."""

    params: GraphicThreeDComponentParams = data.Field(default_factory=GraphicThreeDComponentParams)
