from http import HTTPStatus


def test_excalidraw_page_and_assets(client):
    response = client.get("/excalidraw")
    assert response.status_code == HTTPStatus.OK
    assert "Excalidraw" in response.text
    assert "excalidraw-embed" in response.text

    script = client.get("/excalidraw/app.js")
    assert script.status_code == HTTPStatus.OK
    assert "excalidraw.com" in script.text
