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

"""TheBundle site manifest wiring."""

from __future__ import annotations

from ...core.manifest import SiteManifest
from ...core.static import default_components_path, default_static_path
from .pages import initialize_pages


def site_manifest() -> SiteManifest:
    """Return the manifest for the default TheBundle website site."""
    return SiteManifest(
        title="Bundle Website",
        static_path=default_static_path(),
        components_path=default_components_path(),
        initialize_pages=initialize_pages,
    )
