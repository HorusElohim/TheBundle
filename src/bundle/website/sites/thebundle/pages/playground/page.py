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

"""Playground page showcasing reusable website components."""

from inspect import getfile

from fastapi import Request
from fastapi.responses import HTMLResponse

from bundle.website.builtin import components
from bundle.website.core.templating import PageModule, base_context

page = PageModule(
    __file__,
    name="Playground",
    description="Prototype components quickly with backend and frontend hooks.",
)

COMPONENTS = (
    components.graphic.GraphicTwoDComponent(
        slug="graphic-2d",
        name="Graphic 2D",
        description="Interactive particle network rendered on a 2D canvas.",
        component_file=getfile(components.graphic.GraphicTwoDComponent),
    ),
    components.graphic.GraphicThreeDComponent(
        slug="graphic-3d",
        name="Graphic 3D",
        description="Pseudo-3D starfield with pointer-driven parallax.",
        component_file=getfile(components.graphic.GraphicThreeDComponent),
    ),
    components.WebSocketECCComponent(
        params=components.WebSocketComponentParams(endpoint="/ws/ecc-1")
    ),
    components.WebSocketECCComponent(
        params=components.WebSocketComponentParams(endpoint="/ws/ecc-2")
    ),
    components.WebSocketHeartbeatComponent(),
    components.WebSocketHeartBeatCardioComponent(),
    components.WebSocketHeartBeatMonitorEarthComponent(),
    components.WebSocketHeartBeatMonitorEarthMoonComponent(),
    components.WebSocketToastComponent(),
)

components.attach_routes(page.router, *COMPONENTS)


@page.router.get("/playground", response_class=HTMLResponse)
async def playground(request: Request):
    """Render the playground with all demo components and their assets."""
    page.logger.debug("Rendering playground page")
    context = base_context(request, components.context(*COMPONENTS))
    return page.templates.TemplateResponse(request, "playground.html", context)
