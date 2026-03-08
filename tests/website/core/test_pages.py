from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from bundle.website.core.pages import initialize_pages


@dataclass
class _TestPage:
    name: str
    slug: str
    href: str
    description: str
    router: APIRouter
    static_path: Path | None = None
    show_in_nav: bool = True
    show_on_home: bool = True


def test_initialize_pages_mounts_routes_static_and_nav(tmp_path):
    app = FastAPI()

    demo_static = tmp_path / "demo_static"
    demo_static.mkdir()
    (demo_static / "asset.txt").write_text("demo", encoding="utf-8")

    hidden_static = tmp_path / "hidden_static"
    hidden_static.mkdir()
    (hidden_static / "asset.txt").write_text("hidden", encoding="utf-8")

    demo_router = APIRouter()

    @demo_router.get("/demo", response_class=PlainTextResponse)
    async def demo():
        return "demo-page"

    hidden_router = APIRouter()

    @hidden_router.get("/hidden", response_class=PlainTextResponse)
    async def hidden():
        return "hidden-page"

    pages = (
        _TestPage(
            name="Demo",
            slug="demo",
            href="/demo",
            description="Demo page",
            router=demo_router,
            static_path=demo_static,
        ),
        _TestPage(
            name="Hidden",
            slug="hidden",
            href="/hidden",
            description="Hidden page",
            router=hidden_router,
            static_path=hidden_static,
            show_in_nav=False,
        ),
    )

    registered = initialize_pages(app, pages)
    assert registered == pages
    assert app.state.pages_registry == pages
    assert app.state.nav_pages == (pages[0],)

    with TestClient(app) as client:
        assert client.get("/demo").text == "demo-page"
        assert client.get("/hidden").text == "hidden-page"
        assert client.get("/demo/asset.txt").text == "demo"
        assert client.get("/hidden/asset.txt").text == "hidden"
