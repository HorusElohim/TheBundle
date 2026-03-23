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

from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar

from fastapi import WebSocket

from bundle.core import data
from bundle.website.core.component import COMPONENTS_ROOT, Component

from .backend import create_router, keepalive_loop

__doc__ = """
Base component abstractions for websocket UI blocks.

The base class auto-discovers template/assets from the component folder and
provides a default keepalive websocket behavior that subclasses can override.
"""


class WebSocketComponentParams(data.Data):
    """Shared websocket parameters for component instances."""

    endpoint: str = "/ws/default"

    @data.field_validator("endpoint")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("WebSocket endpoint path must start with '/'")
        return value


class WebSocketBaseComponent(Component):
    """Base websocket component with default params and shared assets."""

    shared_assets: ClassVar[tuple[str, ...]] = ("websocket/base/component.css",)
    params: WebSocketComponentParams = data.Field(default_factory=WebSocketComponentParams)

    @classmethod
    def _resolve_component_asset(cls, asset_path: str) -> str | None:
        candidate = (COMPONENTS_ROOT / asset_path).resolve()
        try:
            return cls._component_relpath(candidate)
        except ValueError:
            return None

    @classmethod
    def shared_asset_paths(cls) -> list[str]:
        paths: list[str] = []
        for asset_name in cls.shared_assets:
            resolved = cls._resolve_component_asset(asset_name)
            if resolved is None:
                continue
            if (COMPONENTS_ROOT / resolved).exists():
                paths.append(resolved)
        return paths

    @classmethod
    def component_asset_paths_for(
        cls,
        component_file: str | Path,
        *,
        asset_filenames: Iterable[str] | None = None,
    ) -> list[str]:
        discovered_paths: list[str] = cls.shared_asset_paths()
        discovered_paths.extend(super().component_asset_paths_for(component_file, asset_filenames=asset_filenames))
        unique_paths = list(dict.fromkeys(discovered_paths))
        return unique_paths

    async def handle_websocket(self, websocket: WebSocket) -> None:
        """Default websocket handler (keepalive protocol)."""
        await keepalive_loop(websocket)

    def build_routers(self):
        """Attach the component websocket route using the configured endpoint."""
        return [create_router(self.params.endpoint, self.handle_websocket)]
