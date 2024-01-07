from pathlib import Path
import platform
import os


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


APP_NAME = "TheBundlePlayer"
PLAYER_PATH = Path(__file__).parent
IMAGE_PATH = PLAYER_PATH / "thebundleplayer.png"
ICON_PATH = PLAYER_PATH / "thebundle_icon.png"
DATA_PATH = get_app_data_path(APP_NAME)
