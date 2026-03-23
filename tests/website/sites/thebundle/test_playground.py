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

from http import HTTPStatus


def test_playground_loads_components(client):
    response = client.get("/playground")
    assert response.status_code == HTTPStatus.OK
    body = response.text
    for marker in (
        'data-component="ws-ecc"',
        'data-component="ws-heartbeat"',
        'data-component="ws-toast"',
    ):
        assert marker in body
    assert 'data-component="ws-ecc" data-ws-path="/ws/ecc-1"' in body
    assert 'data-component="ws-ecc" data-ws-path="/ws/ecc-2"' in body


def test_playground_keepalive_websocket(client):
    sent_at = 123
    with client.websocket_connect("/ws/ecc-1") as websocket:
        websocket.send_json({"type": "keepalive", "sent_at": sent_at})
        payload = websocket.receive_json()

    assert payload["type"] == "keepalive_ack"
    assert payload["sent_at"] == sent_at
    assert isinstance(payload["received_at"], int)


def test_heartbeat_keepalive_websocket(client):
    sent_at = 456
    with client.websocket_connect("/ws/heartbeat") as websocket:
        websocket.send_json({"type": "keepalive", "sent_at": sent_at})
        payload = websocket.receive_json()

    assert payload["type"] == "keepalive_ack"
    assert payload["sent_at"] == sent_at
    assert isinstance(payload["received_at"], int)


def test_toast_websocket_streams_messages(client):
    with client.websocket_connect("/ws/toast") as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "toast"
    assert "Server ping" in payload["body"]


def test_component_static_assets_are_served(client):
    response = client.get("/components-static/websocket/base/component.js")
    assert response.status_code == HTTPStatus.OK
    assert "getWebSocketChannel" in response.text
