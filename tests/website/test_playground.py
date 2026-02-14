from http import HTTPStatus


def test_playground_loads_components(client):
    response = client.get("/playground")
    assert response.status_code == HTTPStatus.OK
    body = response.text
    for marker in ('data-component="ws-ecc"', 'data-component="ws-heartbeat"', 'data-component="ws-toast"'):
        assert marker in body


def test_playground_keepalive_websocket(client):
    sent_at = 123
    with client.websocket_connect("/ws/ecc") as websocket:
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
    response = client.get("/components-static/websocket/base/frontend/ws.js")
    assert response.status_code == HTTPStatus.OK
    assert "getWebSocketChannel" in response.text
