from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from bundle.audio.engine import SUPPORTED_EXTENSIONS
from bundle.core import logger
from bundle.core.app_data import get_app_data_path

UPLOAD_DIR = get_app_data_path("bundle.audio") / "uploads"
log = logger.get_logger(__name__)


def ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    log.debug("Upload directory ready: %s", UPLOAD_DIR)
    return UPLOAD_DIR


def save_upload(upload: UploadFile) -> Path:
    filename = (upload.filename or "").strip()
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        log.warning("Rejected upload suffix: %s", suffix)
        raise ValueError(f"Unsupported audio format: {suffix or 'unknown'}")

    upload_dir = ensure_upload_dir()
    safe_name = f"{uuid4().hex}{suffix}"
    destination = upload_dir / safe_name

    with destination.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)

    log.info("Saved upload: %s (%s)", destination, suffix)
    return destination
