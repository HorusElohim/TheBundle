import logging
from pathlib import Path


def get_template_path(file_path) -> Path:
    return Path(file_path).parent / "templates"


def get_static_path(file_path) -> Path:
    return Path(file_path).parent / "static"


def get_logger(page_name: str):
    return logging.getLogger(f"bundle.website.{page_name}")
