from pathlib import Path
import platform
import os
from ...core import setup_logging
import shutil

import sys
from pathlib import Path
from os import getenv


def get_app_data_path(app_name):
    if sys.platform == "win32":
        app_data = Path().home().absolute() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        app_data = Path("~/Library/Application Support/").expanduser()
    else:
        app_data = Path(getenv("XDG_DATA_HOME", "~/.local/share")).expanduser()
    return app_data / app_name


APP_NAME = "TheBundleGPT"
CODE_PATH = Path(__file__).parent
DATA_PATH = get_app_data_path(APP_NAME)
# shutil.rmtree(str(DATA_PATH))
DATA_PATH.mkdir(mode=0o777, exist_ok=True)
LOG_PATH = DATA_PATH / "logs"
LOG_PATH.mkdir(parents=True, exist_ok=True)

LOGGER = setup_logging(name="gpt", log_path=LOG_PATH, level=10)


from .client import GPTClient
from .agent import Agent
from .orchestrator import AgentOrchestrator
from .cli import main

LOGGER.debug(f"gpt module loaded. Data dir: {DATA_PATH}. Log dir {LOG_PATH}.")
