"""Excalidraw page route wiring."""

from fastapi import Request
from fastapi.responses import HTMLResponse

from bundle.website.core.templating import PageModule, base_context

page = PageModule(
    __file__,
    name="Excalidraw",
    description="Draw and brainstorm with the Excalidraw canvas.",
)


@page.router.get("/excalidraw", response_class=HTMLResponse)
async def excalidraw_page(request: Request):
    """Render the Excalidraw host page."""
    context = base_context(request, {"title": "Excalidraw"})
    return page.templates.TemplateResponse(request, "index.html", context)
