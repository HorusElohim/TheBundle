from http import HTTPStatus


def test_ble_dashboard_loads(client):
    response = client.get("/ble")
    assert response.status_code == HTTPStatus.OK
    assert "BLE" in response.text
