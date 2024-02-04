import re
from pathlib import Path
from sys import platform


def sanitize_pathname(path: Path) -> Path:
    invalid_chars = r'[<>:"/\\|?*\0\n\r]' if platform.startswith("win") else r"[/\0\n\r]"
    sanitized_stem = re.sub(invalid_chars, "", path.stem)
    return path.with_name(sanitized_stem + path.suffix)


from .mp3 import MP3, MP3_PATH
from .mp4 import MP4, MP4_PATH
