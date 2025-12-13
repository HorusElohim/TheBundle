from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.staticfiles import StaticFiles

from .. import common
from . import ble, home, youtube

LOGGER = common.sections.get_logger("sections")


@dataclass(frozen=True)
class SectionDefinition:
    name: str
    slug: str
    href: str
    description: str
    router: Any
    static_path: Path
    show_in_nav: bool = True
    show_on_home: bool = True


SECTION_REGISTRY: tuple[SectionDefinition, ...] = (
    SectionDefinition(
        name="Home",
        slug="home",
        href="/",
        description="Choose a lab to explore.",
        router=home.router,
        static_path=home.STATIC_PATH,
    ),
    SectionDefinition(
        name="BLE",
        slug="ble",
        href="/ble",
        description="Scan, inspect, and connect to Nordic UART devices in real time.",
        router=ble.router,
        static_path=ble.STATIC_PATH,
    ),
    SectionDefinition(
        name="YouTube",
        slug="youtube",
        href="/youtube",
        description="Resolve and download tracks directly into The Bundle workbench.",
        router=youtube.router,
        static_path=youtube.STATIC_PATH,
    ),
)


def mount_section(app, section: SectionDefinition):
    token = f"✨({section.slug})"
    LOGGER.debug("%s registering section..", token)
    LOGGER.debug("%s router", token)
    app.include_router(section.router)
    LOGGER.debug("%s static: %s", token, section.static_path)
    app.mount(
        f"/{section.slug}",
        StaticFiles(directory=str(section.static_path)),
        name=section.slug,
    )
    LOGGER.debug("%s registered", token)


def initialize_sections(app):
    for section in SECTION_REGISTRY:
        mount_section(app, section)

    app.state.sections_registry = SECTION_REGISTRY
    app.state.nav_sections = tuple(section for section in SECTION_REGISTRY if section.show_in_nav)
