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
from bundle.website.core.component import Component

__doc__ = """
Base component abstractions for graphics UI blocks.

The base class auto-discovers template/assets from the component folder and
provides shared typed params for graphics-oriented components.
"""


class GraphicComponentParams(data.Data):
    """Shared parameters for graphics component instances."""

    graph_id: str = "graphics"
    render_mode: str = "base"


class GraphicBaseComponent(Component):
    """Base graphics component with shared typed params."""

    params: GraphicComponentParams = data.Field(default_factory=GraphicComponentParams)
