from http import HTTPStatus


def test_home_renders(client):
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    body = response.text
    for name in ("BLE", "YouTube", "Excalidraw"):
        assert name in body
    assert "bundle website site start bundle" in body
    assert "__BUNDLE_WEBSITE_RUNTIME__" in body
