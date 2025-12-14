from http import HTTPStatus


def test_youtube_page_loads(client):
    response = client.get("/youtube")
    assert response.status_code == HTTPStatus.OK
    assert "YouTube" in response.text
