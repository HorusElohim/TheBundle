import os
import platform
from pathlib import Path


def get_app_data_path(app_name: str) -> Path:
    system = platform.system()

    match system:
        case "Windows":
            app_data_dir = Path(os.environ["APPDATA"]) / app_name
        case "Darwin":
            app_data_dir = Path.home() / "Library/Application Support" / app_name
        case _:
            app_data_dir = Path.home() / ".local/share" / app_name

    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir


YOUTUBE_PATH = get_app_data_path("bundle.youtube")
POTO_TOKEN_PATH = YOUTUBE_PATH / "poto_token.json"
