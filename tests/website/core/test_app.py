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

import json

from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from bundle.website.core.app import create_app
from bundle.website.core.manifest import SiteManifest


def test_create_app_uses_manifest_and_mounts_assets(tmp_path):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "favicon.ico").write_bytes(b"ico")
    (static_dir / "site.webmanifest").write_text('{"name":"test"}', encoding="utf-8")

    components_dir = tmp_path / "components"
    component_subdir = components_dir / "demo"
    component_subdir.mkdir(parents=True)
    (component_subdir / "component.js").write_text(
        "console.log('ok');", encoding="utf-8"
    )
    (component_subdir / "component.py").write_text("print('secret')", encoding="utf-8")

    called = {"initialized": False}

    def initialize_pages(app):
        called["initialized"] = True

        @app.get("/custom", response_class=PlainTextResponse)
        async def custom():
            return "custom-page"

    manifest = SiteManifest(
        title="Custom Test Site",
        static_mount_path="/assets",
        components_mount_path="/widgets-static",
        static_path=static_dir,
        components_path=components_dir,
        initialize_pages=initialize_pages,
    )
    app = create_app(manifest)

    assert app.title == "Custom Test Site"
    assert called["initialized"] is True
    assert app.state.asset_version.isdigit()
    assert app.state.static_mount_path == "/assets"
    assert app.state.components_mount_path == "/widgets-static"

    with TestClient(app) as client:
        assert client.get("/custom").text == "custom-page"
        assert client.get("/favicon.ico").status_code == 200
        webmanifest = client.get("/site.webmanifest")
        assert webmanifest.status_code == 200
        assert webmanifest.json() == {"name": "test"}

        allowed = client.get("/widgets-static/demo/component.js")
        assert allowed.status_code == 200
        assert "console.log" in allowed.text

        blocked = client.get("/widgets-static/demo/component.py")
        assert blocked.status_code == 404

        csp_json = client.post(
            "/csp-report", json={"csp-report": {"blocked-uri": "inline"}}
        )
        assert csp_json.status_code == 204

        csp_raw = client.post(
            "/csp-report",
            content=json.dumps({"sample": "raw"}).encode("utf-8"),
            headers={"content-type": "application/csp-report"},
        )
        assert csp_raw.status_code == 204
