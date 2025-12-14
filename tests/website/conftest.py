import pytest
from fastapi.testclient import TestClient

from bundle.website import get_app


@pytest.fixture(scope="session")
def app():
    return get_app()


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client
