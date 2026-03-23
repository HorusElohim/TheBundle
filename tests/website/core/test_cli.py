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

from click.testing import CliRunner

from bundle.website import cli as website_cli


def test_website_cli_exposes_site_group():
    runner = CliRunner()
    result = runner.invoke(website_cli.website, ["--help"])
    assert result.exit_code == 0
    assert "site" in result.output


def test_website_site_start_bundle_invokes_uvicorn(monkeypatch):
    captured = {}

    def fake_run(app, host, port):
        captured["host"] = host
        captured["port"] = port
        captured["title"] = app.title

    monkeypatch.setattr(website_cli.uvicorn, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(
        website_cli.website,
        ["site", "start", "bundle", "--host", "127.0.0.1", "--port", "9001"],
    )
    assert result.exit_code == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9001
    assert captured["title"] == "Bundle Website"


def test_website_site_build_help_exposes_site_argument():
    runner = CliRunner()
    result = runner.invoke(website_cli.website, ["site", "build", "--help"])
    assert result.exit_code == 0
    assert "{bundle}" in result.output
