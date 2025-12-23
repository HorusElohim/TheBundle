from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse

from bundle.core import logger

from .stream import create_stream
from .uploads import UPLOAD_DIR, save_upload

router = APIRouter()
log = logger.get_logger(__name__)


@router.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket) -> None:
    stream = create_stream(websocket)
    await stream.run()


@router.get("/api/audio/health")
async def audio_health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/audio/upload")
async def audio_upload(file: UploadFile = File(...)) -> dict[str, str]:
    try:
        log.info("Audio upload: name=%s content_type=%s", file.filename, file.content_type)
        path = save_upload(file)
    except ValueError as exc:
        log.error("Audio upload rejected: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()
    log.info("Audio upload saved: path=%s", path)
    return {"path": str(path), "url": f"/api/audio/file/{path.name}"}


@router.get("/api/audio/file/{filename}")
async def audio_file(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    path = UPLOAD_DIR / safe_name
    if not path.exists():
        log.warning("Audio file not found: %s", path)
        raise HTTPException(status_code=404, detail="Audio file not found")
    log.debug("Audio file served: %s", path)
    return FileResponse(path)
