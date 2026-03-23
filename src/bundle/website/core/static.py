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

"""Static path helpers and guarded component static file serving."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles


def website_root() -> Path:
    """Return the website package root directory."""
    return Path(__file__).resolve().parents[1]


def default_static_path() -> Path:
    """Return the default global static directory for the website app."""
    return website_root() / "static"


def default_components_path() -> Path:
    """Return the default components root directory for static mounting."""
    return website_root() / "builtin" / "components"


class ComponentStaticFiles(StaticFiles):
    """
    Serve only safe static asset types from component folders.

    The allowlist blocks Python/templates and only exposes frontend-oriented
    asset types. This supports the atomic component layout
    (`component.ts` / `component.css` at component root plus optional `assets/`).
    """

    _ALLOWED_SUFFIXES = {
        ".js",
        ".mjs",
        ".css",
        ".map",
        ".json",
        ".png",
        ".jpg",
        ".jpeg",
        ".hdr",
        ".svg",
        ".woff",
        ".woff2",
    }

    async def get_response(self, path: str, scope):  # type: ignore[override]
        # Defensive normalization in case the incoming path still includes query/fragment tokens.
        clean_path = path.split("?", 1)[0].split("#", 1)[0].strip("/")
        rel_path = clean_path.replace("\\", "/")
        suffix = Path(rel_path).suffix.lower()
        if suffix not in self._ALLOWED_SUFFIXES:
            return Response(status_code=404)
        return await super().get_response(rel_path, scope)
