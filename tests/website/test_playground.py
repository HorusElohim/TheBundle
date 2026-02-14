from http import HTTPStatus


def test_playground_loads_widgets(client):
    response = client.get("/playground")
    assert response.status_code == HTTPStatus.OK
    body = response.text
    for marker in ('data-widget="ws-ecc"', 'data-widget="ws-heartbeat"', 'data-widget="ws-toast"'):
        assert marker in body


def test_playground_keepalive_websocket(client):
    sent_at = 123
    with client.websocket_connect("/ws/ecc") as websocket:
        websocket.send_json({"type": "keepalive", "sent_at": sent_at})
        payload = websocket.receive_json()

    assert payload["type"] == "keepalive_ack"
    assert payload["sent_at"] == sent_at
    assert isinstance(payload["received_at"], int)


def test_widget_static_assets_are_served(client):
    response = client.get("/widgets-static/websocket/base/frontend/ws.js")
    assert response.status_code == HTTPStatus.OK
    assert "getWebSocketChannel" in response.text
