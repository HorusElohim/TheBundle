# Bundle Website

This folder contains the FastAPI-powered marketing/utility site for The Bundle. Key files:

- `__init__.py`: `get_app()` mounts `/static`, registers sections, serves favicon/manifest.
- `templates/base.html`: shared head + global navbar + page shell used by every section.
- `static/theme.css`: global tokens, nav styling, scrollbar fixes.
- `sections/home/home.py`, `sections/ble/ble.py`, `sections/youtube/home.py`: section routers.
- `sections/__init__.py`: `SectionDefinition` registry + static/router mounting.
- `common/sections.py`: helpers `get_template_path`, `get_static_path`, `create_templates`, `base_context`.

## Design system
- Global layout: `base.html` + `theme.css` give a modern, translucent navbar with a reserved actions slot (for status pills).
- Shared tokens: font stack, radius, nav colors live in `static/theme.css`; per-section CSS sets its own accents/backgrounds.
- Scroll stability: `html` forces a scrollbar to prevent navbar jitter; `scrollbar-gutter: stable` is enabled globally.

## Adding a new section (with example)
Follow the pattern used by BLE (`sections/ble/ble.py`) and YouTube (`sections/youtube/home.py`).

1) **Create files**
- `sections/blog/__init__.py` (can be empty).
- `sections/blog/blog.py` (router + paths).
- `sections/blog/templates/blog.html` (extends `base.html`).
- `sections/blog/static/styles.css` and optional `app.js`.

2) **Router module** (`sections/blog/blog.py`)
```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ...common.sections import create_templates, base_context, get_logger, get_template_path, get_static_path

NAME = "blog"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)

@router.get("/blog", response_class=HTMLResponse)
async def blog(request: Request):
    return templates.TemplateResponse("blog.html", base_context(request, {"title": "Bundle Blog"}))
```

3) **Template** (`sections/blog/templates/blog.html`)
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
Place styles in `sections/blog/static/styles.css` (define accent colors, layout), and JS in `sections/blog/static/app.js` if needed.

5) **Register the section** (`sections/__init__.py`)  
Add a registry entry:
```python
SectionDefinition(
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
`sections/home/home.py` reads `app.state.sections_registry`; any entry with `show_on_home=True` appears on the landing cards. Navbar links render from `nav_sections` (entries with `show_in_nav=True`).

7) **Run and verify**  
Start the site: `bundle website start` → visit `/blog` → confirm `/blog/styles.css` loads and the nav highlights “Blog.”
