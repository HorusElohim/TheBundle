import os
from bundle.core import platform_info
from pathlib import Path


def get_app_data_path(app_name: str) -> Path:

    match platform_info.system:
        case "windows":
            app_data_dir = Path(os.environ["APPDATA"]) / app_name
        case "darwin":
            app_data_dir = Path.home() / "Library/Application Support" / app_name
        case "linux":
            app_data_dir = Path.home() / ".local/share" / app_name
        case _:
            raise ValueError(f"Unsupported platform: {platform_info.system}")

    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir


YOUTUBE_PATH = get_app_data_path("bundle.youtube")
POTO_TOKEN_PATH = YOUTUBE_PATH / "poto_token.json"
