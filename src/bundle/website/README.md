# Bundle Website

This folder contains the FastAPI-powered marketing/utility site for The Bundle. Key files:

- `__init__.py`: `get_app()` mounts `/static`, registers pages, serves favicon/manifest.
- `templates/base.html`: shared head + global navbar + page shell used by every page.
- `static/theme.css`: global tokens, nav styling, scrollbar fixes.
- `pages/home/home.py`, `pages/ble/ble.py`, `pages/youtube/home.py`: page routers.
- `pages/__init__.py`: `PageDefinition` registry + static/router mounting.
- `common/pages.py`: helpers `get_template_path`, `get_static_path`, `create_templates`, `base_context`.
- `components/`: reusable page-attached components (templates, assets, backend behavior).

## Install & run
- Install website deps: `pip install -e ".[website]"`
- Start the server (from repo root): `bundle website start`
- Navigate to `http://127.0.0.1:8000/` (pages like `/ble`, `/youtube`, `/excalidraw`)

## Design system
- Global layout: `base.html` + `theme.css` give a modern, translucent navbar with a reserved actions slot (for status pills).
- Shared tokens: font stack, radius, nav colors live in `static/theme.css`; per-page CSS sets its own accents/backgrounds.
- Scroll stability: `html` forces a scrollbar to prevent navbar jitter; `scrollbar-gutter: stable` is enabled globally.

## Component architecture

The website uses page-scoped components for composability and scale.

- Components live under `src/bundle/website/components/`.
- Pages explicitly instantiate components and attach routes.
- Static assets are discovered from each component folder (`frontend/`).
- Templates are rendered via page context/macros from component definitions.

Websocket components follow a shared base architecture:

- `WebSocketBaseComponent` defines common defaults and routing behavior.
- `base/backend.py` provides composable runtime blocks (`run_websocket`, `every`, `drain_text`, `receive_json`, `MessageRouter`).
- `base/messages.py` defines typed `Data` messages (`KeepAliveMessage`, `AckMessage`, `ErrorMessage`).

This keeps code minimal: route wiring is inherited, and only protocol-specific behavior is overridden.

For details and examples, see `src/bundle/website/components/README.md`.

## Adding a new page (with example)
Follow the pattern used by BLE (`pages/ble/ble.py`) and YouTube (`pages/youtube/home.py`).

1) **Create files**
- `pages/blog/__init__.py` (can be empty).
- `pages/blog/blog.py` (router + paths).
- `pages/blog/templates/blog.html` (extends `base.html`).
- `pages/blog/static/styles.css` and optional `app.js`.

2) **Router module** (`pages/blog/blog.py`)
```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ...common.pages import create_templates, base_context, get_logger, get_template_path, get_static_path

NAME = "blog"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)

@router.get("/blog", response_class=HTMLResponse)
async def blog(request: Request):
    return templates.TemplateResponse(request, "blog.html", base_context(request, {"title": "Bundle Blog"}))
```

3) **Template** (`pages/blog/templates/blog.html`)
```jinja2
{% extends "base.html" %}
{% block title %}Bundle • Blog{% endblock %}
{% block styles %}<link rel="stylesheet" href="{{ url_for('blog', path='styles.css') }}">{% endblock %}
{% block content %}
<div class="page">
  <main class="content">
    <h1>Bundle Blog</h1>
    <p class="muted">Coming soon.</p>
  </main>
</div>
{% endblock %}
{% block scripts %}<script type="module" src="{{ url_for('blog', path='app.js') }}"></script>{% endblock %}
```

4) **CSS/JS**  
Place styles in `pages/blog/static/styles.css` (define accent colors, layout), and JS in `pages/blog/static/app.js` if needed.

5) **Register the page** (`pages/__init__.py`)  
Add a registry entry:
```python
PageDefinition(
    name="Blog",
    slug="blog",
    href="/blog",
    description="Updates from the Bundle team.",
    router=blog.router,
    static_path=blog.STATIC_PATH,
    show_in_nav=True,
    show_on_home=True,
),
```

6) **Home cards and nav**  
`pages/home/home.py` reads `app.state.pages_registry`; any entry with `show_on_home=True` appears on the landing cards. Navbar links render from `nav_pages` (entries with `show_in_nav=True`).

7) **Run and verify**  
Start the site: `bundle website start` → visit `/blog` → confirm `/blog/styles.css` loads and the nav highlights “Blog.”

## Excalidraw (self-hosted)
- Source: `src/bundle/website/vendor/excalidraw` (submodule; branch/tag as configured).
- Served bundle: `src/bundle/website/pages/excalibur/static/excalidraw-web/` (copied build output).
- PWA is disabled by default; enable by setting `VITE_APP_ENABLE_PWA=true` before build.

### Update / rebuild the bundle
1. Update the submodule (or fork checkout) to the desired ref:
   ```sh
   git submodule update --init --recursive
   cd src/bundle/website/vendor/excalidraw
   git fetch && git checkout <ref>
   ```
2. Build with Node 18–22 (ignore engines with `YARN_IGNORE_ENGINES=1` if needed):
   ```sh
   YARN_IGNORE_ENGINES=1 corepack yarn --cwd src/bundle/website/vendor/excalidraw/excalidraw-app build:app
   ```
3. Replace the served assets:
   ```sh
   rm -rf src/bundle/website/pages/excalibur/static/excalidraw-web
   cp -R src/bundle/website/vendor/excalidraw/excalidraw-app/build/* src/bundle/website/pages/excalibur/static/excalidraw-web/
   ```
4. Restart the dev server and hard-reload `/excalidraw` (clearing any cached service worker).
