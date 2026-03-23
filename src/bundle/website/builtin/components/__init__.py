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

"""Built-in website components and UI helpers."""

from bundle.website.core.component import (
    Component,
    ComponentAsset,
    ComponentAssets,
    attach_routes,
    context,
)

from . import graphic, websocket
from .websocket.base import (
    GPXComponentParams,
    GPXWebSocketBaseComponent,
    WebSocketBaseComponent,
    WebSocketComponentParams,
)
from .websocket.ecc import WebSocketECCComponent
from .websocket.heartbeat import WebSocketHeartbeatComponent
from .websocket.heartbeat_cardio import WebSocketHeartBeatCardioComponent
from .websocket.heartbeat_earth import WebSocketHeartBeatMonitorEarthComponent
from .websocket.heartbeat_earth_moon import WebSocketHeartBeatMonitorEarthMoonComponent
from .websocket.toast import WebSocketToastComponent

__all__ = [
    "Component",
    "ComponentAsset",
    "ComponentAssets",
    "GPXComponentParams",
    "GPXWebSocketBaseComponent",
    "WebSocketBaseComponent",
    "WebSocketComponentParams",
    "WebSocketECCComponent",
    "WebSocketHeartBeatCardioComponent",
    "WebSocketHeartBeatMonitorEarthComponent",
    "WebSocketHeartBeatMonitorEarthMoonComponent",
    "WebSocketHeartbeatComponent",
    "WebSocketToastComponent",
    "attach_routes",
    "context",
    "graphic",
    "websocket",
]
