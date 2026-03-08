"""Home page routes for the Bundle website."""

from fastapi import Request
from fastapi.responses import HTMLResponse

from bundle.website.core.templating import PageModule, base_context

page = PageModule(
    __file__,
    name="Home",
    href="/",
    description="Choose a lab to explore.",
)


@page.router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page with cards for all registered non-home pages."""
    pages_registry = getattr(request.app.state, "pages_registry", [])
    page_cards = [p for p in pages_registry if p.slug != "home" and p.show_on_home]
    context = base_context(request, {"pages": page_cards})
    return page.templates.TemplateResponse(request, "index.html", context)
