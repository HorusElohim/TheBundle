from fastapi.staticfiles import StaticFiles

from .. import common
from . import home, youtube

LOGGER = common.sections.get_logger("sections")


def init_section(app, section_module):
    S = f"✨({section_module.NAME})"
    LOGGER.debug("%s registering section..", S)
    LOGGER.debug("%s static: %s", S, section_module.STATIC_PATH)
    app.mount(f"/{section_module.NAME}", StaticFiles(directory=str(section_module.STATIC_PATH)), name=section_module.NAME)
    LOGGER.debug("%s router", S)
    app.include_router(section_module.router)
    LOGGER.debug("%s registered", S)


def initialize_sections(app):
    init_section(app, home)
    init_section(app, youtube)
