from pathlib import Path

from bundle.core.app_data import get_app_data_path

YOUTUBE_PATH = get_app_data_path("bundle.youtube")
POTO_TOKEN_PATH = YOUTUBE_PATH / "poto_token.json"
