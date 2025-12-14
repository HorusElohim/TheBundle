from http import HTTPStatus


def test_home_renders(client):
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    body = response.text
    for name in ("BLE", "YouTube", "Excalibur"):
        assert name in body
