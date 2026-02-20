# Bundle Website

This package contains the FastAPI website for The Bundle.

## High-level architecture

- App entrypoint: `src/bundle/website/__init__.py`
- Core app factory and policies: `src/bundle/website/core/`
- Page registry and mounting: `src/bundle/website/pages/__init__.py`
- Shared page/template helpers: `src/bundle/website/core/templating.py`
- Shared layout + global theme: `src/bundle/website/templates/base.html`, `src/bundle/website/static/theme.css`
- Reusable page-scoped components: `src/bundle/website/components/`

The app mounts:

- `/static` -> `src/bundle/website/static`
- `/components-static` -> `src/bundle/website/components` (served through `ComponentStaticFiles` suffix allowlist)

## Install and run

- Install website extras: `pip install -e ".[website]"`
- Start server: `bundle website start`
- Open: `http://127.0.0.1:8000/`

## Frontend build commands

- Install frontend tooling/deps: `bundle website install`
- Build frontend assets: `bundle website build`
- Type-check website TS only: `cd src/bundle/website && npm run check:website-ts`

## Pages

Pages are registered in `src/bundle/website/pages/__init__.py` using `PageDefinition`.

Each page module typically defines:

- `router`
- `TEMPLATE_PATH`
- `STATIC_PATH`
- one or more route handlers returning `TemplateResponse`

`initialize_pages(app)` mounts every page router and page static folder and publishes nav data on `app.state`.

## Component system

Components are page-scoped and explicit:

- Create component instances in the page module.
- Attach websocket/API routes with `components.attach_routes(router, *COMPONENTS)`.
- Pass render/assets context with `components.context(*COMPONENTS)`.
- Render in template via `templates/components/macros.html`.

The macros provide:

- `styles(component_assets)` -> emits component CSS links
- `scripts(component_assets)` -> emits component JS links
- `render(components)` -> includes each component template

## How to create a new component

This is the current recommended flow.

### 1. Create component folder

Use one folder per component:

```text
src/bundle/website/components/<domain>/<name>/
  component.py
  template.html
  component.css  (optional)
  component.ts   (optional)
  component.js   (built)
  assets/        (optional)
```

### 2. Choose a base class

- Websocket component: inherit `WebSocketBaseComponent`
  - file: `src/bundle/website/components/websocket/base/component.py`
- Graphics component: inherit `GraphicBaseComponent` / typed 2D/3D variants
  - file: `src/bundle/website/components/graphic/base/component.py`

The base classes auto-hydrate:

- `template` from local `template.html`
- `assets` from local component root (`component.css`, `component.js`, `component.mjs`)

### 3. Implement `component.py`

Minimal websocket example:

```python
from ..base import WebSocketBaseComponent, WebSocketComponentParams


class WebSocketExampleComponent(WebSocketBaseComponent):
    component_file: str = __file__
    slug: str = "ws-example"
    name: str = "WebSocket Example"
    description: str = "Example websocket component."
    params: WebSocketComponentParams = WebSocketComponentParams(endpoint="/ws/example")
```

Override `handle_websocket(self, websocket)` only when you need custom runtime behavior.

### 4. Build `template.html`

Use `component.slug`/`component.params.ws_path` pattern and stable `data-*` selectors for JS hooks.

Websocket UI should use shared panel structure classes:

- root: `ws-panel <component-class>`
- blocks: `ws-panel__header`, `ws-panel__badges`, `ws-panel__viewport`, `ws-panel__controls`, etc.

### 5. Add frontend assets

Put CSS/JS at component root (`component.css`, `component.ts` -> `component.js`).

For websocket components:

- shared base stylesheet is loaded automatically via `WebSocketBaseComponent.shared_assets`
- current shared stylesheet: `websocket/base/component.css`
- local component CSS should mostly set variables and minimal overrides

### 6. Attach component to a page

In page module (for example `pages/playground/playground.py`):

```python
COMPONENTS = (
    websocket.example.WebSocketExampleComponent(),
)

components.attach_routes(router, *COMPONENTS)
```

In the page handler:

```python
context = base_context(request, components.context(*COMPONENTS))
return templates.TemplateResponse(request, "playground.html", context)
```

In the page template:

```jinja2
{% import "components/macros.html" as component_macros with context %}

{% block styles %}
{{ component_macros.styles(component_assets) }}
{% endblock %}

{% block content %}
{{ component_macros.render(components) }}
{% endblock %}

{% block scripts %}
{{ component_macros.scripts(component_assets) }}
{% endblock %}
```

## Websocket internals

`src/bundle/website/components/websocket/base` provides:

- route/runtime helpers: `create_router`, `run_websocket`, `every`, `drain_text`, `receive_json`, `keepalive_loop`
- typed message models: `KeepAliveMessage`, `AckMessage`, `ErrorMessage`
- message dispatch helper: `MessageRouter`

Use these blocks instead of custom ad-hoc websocket loops when possible.

## Security and static serving notes

- Component static mount only serves allowed static asset suffixes (`.css`, `.js`, `.mjs`, `.map`, fonts/images, etc.).
- Python source files under `components/` are not exposed by `/components-static`.

## Excalidraw vendor workflow

- Vendor source: `src/bundle/website/vendor/excalidraw`
- Served build: `src/bundle/website/pages/excalibur/static/excalidraw-web`

Typical update flow:

1. `git submodule update --init --recursive`
2. checkout desired vendor ref
3. build vendor app
4. copy built assets into `pages/excalibur/static/excalidraw-web`
