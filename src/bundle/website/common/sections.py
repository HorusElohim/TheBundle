import logging
from pathlib import Path
from typing import Any, Iterable, Mapping

from fastapi.templating import Jinja2Templates


def get_template_path(file_path) -> Path:
    return Path(file_path).parent / "templates"


def get_static_path(file_path) -> Path:
    return Path(file_path).parent / "static"


def get_logger(page_name: str):
    return logging.getLogger(f"bundle.website.{page_name}")


BASE_TEMPLATE_PATH = Path(__file__).parent.parent / "templates"


def create_templates(*template_roots: Iterable[Path] | Path) -> Jinja2Templates:
    """
    Create a Jinja environment that can resolve both section templates and shared layout files.
    Accepts one or more template directories; will always append the shared base template path.
    """
    paths: list[Path] = []
    for root in template_roots:
        if isinstance(root, (str, Path)):
            paths.append(Path(root))
        else:
            paths.extend(Path(p) for p in root)
    paths.append(BASE_TEMPLATE_PATH)
    search_paths = [str(path) for path in paths]
    return Jinja2Templates(directory=search_paths)


def base_context(request: Any, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """
    Shared context payload for templates so we only wire request/nav data once.
    """
    extra = extra or {}
    nav_sections = getattr(getattr(request, "app", None), "state", None)
    nav_sections = getattr(nav_sections, "nav_sections", [])
    return {"request": request, "nav_sections": nav_sections, **extra}
