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

from fastapi import APIRouter

from bundle.website.builtin import components


def test_websocket_component_defaults():
    default = components.WebSocketHeartbeatComponent()
    assert default.slug == "ws-heartbeat"
    assert default.params.endpoint == "/ws/heartbeat"
    assert any(asset.path.endswith("heartbeat/component.js") for asset in default.assets)
    assert all(asset.route_name == "components_static" for asset in default.assets)


def test_component_context_supports_data_params_override():
    custom = components.WebSocketHeartbeatComponent(params=components.WebSocketComponentParams(endpoint="/ws/custom"))
    ctx = components.context(custom)
    selected = ctx["components"]
    assert len(selected) == 1
    assert selected[0].params is not None and selected[0].params.endpoint == "/ws/custom"


def test_component_context_accepts_component_instance():
    custom = components.WebSocketECCComponent(params=components.WebSocketComponentParams(endpoint="/ws/ecc-alt"))
    ctx = components.context(custom)
    selected = ctx["components"]
    assert len(selected) == 1
    assert selected[0].slug == "ws-ecc"
    assert selected[0].params.endpoint == "/ws/ecc-alt"


def test_attach_routes_is_page_scoped():
    router = APIRouter()
    components.attach_routes(router, components.WebSocketHeartbeatComponent())
    paths = {route.path for route in router.routes}
    assert "/ws/heartbeat" in paths
    assert "/ws/toast" not in paths
    assert "/ws/ecc" not in paths


def test_attach_routes_supports_multiple_ecc_instances():
    router = APIRouter()
    components.attach_routes(
        router,
        components.WebSocketECCComponent(params=components.WebSocketComponentParams(endpoint="/ws/ecc-1")),
        components.WebSocketECCComponent(params=components.WebSocketComponentParams(endpoint="/ws/ecc-2")),
    )
    paths = {route.path for route in router.routes}
    assert "/ws/ecc-1" in paths
    assert "/ws/ecc-2" in paths


def test_graphic_component_exports_are_available():
    assert components.graphic.GraphicBaseComponent is not None
    assert components.graphic.GraphicTwoDComponent is not None
    assert components.graphic.GraphicThreeDComponent is not None


def test_graphic_3d_default_params():
    component = components.graphic.GraphicThreeDComponent(slug="graphic-3d")
    assert isinstance(component.params, components.graphic.GraphicThreeDComponentParams)
    assert component.params.render_mode == "3d"
    assert component.params.camera_mode == "orbit"


def test_gpx_websocket_base_inherits_graphic_3d_defaults():
    component = components.WebSocketHeartBeatMonitorEarthComponent()
    assert isinstance(component, components.GPXWebSocketBaseComponent)
    assert component.params.render_mode == "3d"
    assert component.params.graph_id == "heartbeat-earth"


def test_heartbeat_cardio_component_defaults():
    component = components.WebSocketHeartBeatCardioComponent()
    assert isinstance(component, components.GPXWebSocketBaseComponent)
    assert component.slug == "ws-heartbeat-cardio"
    assert component.params.endpoint == "/ws/heartbeat-cardio"
    assert component.params.graph_id == "heartbeat-cardio"
