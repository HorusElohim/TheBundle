from __future__ import annotations

from fastapi import WebSocket, WebSocketDisconnect

from bundle.core import logger
from bundle.usd import ErrorEvent, LoadScene, SceneLoaded, USDScene

from ...common.websocket import WebSocketDataMixin
from .usd import LOGGER, router

LOG = logger.get_logger(__name__)


class LoadSceneMessage(LoadScene, WebSocketDataMixin):
    pass


class SceneLoadedMessage(SceneLoaded, WebSocketDataMixin):
    pass


class ErrorEventMessage(ErrorEvent, WebSocketDataMixin):
    pass


@router.websocket("/ws/usd")
async def usd_websocket(websocket: WebSocket):
    await websocket.accept()
    LOG.debug("USD websocket connection established: %s", websocket.client)
    while True:
        try:
            message = await LoadSceneMessage.receive(websocket)
        except WebSocketDisconnect:
            LOG.debug("USD websocket disconnected: %s", websocket.client)
            break
        except Exception as exc:  # pragma: no cover - requires websocket session
            LOG.warning("Invalid USD websocket payload: %s", exc)
            await ErrorEventMessage(message="Invalid payload", detail=str(exc)).send(websocket)
            continue

        try:
            scene = USDScene.open(message.path)
            info = scene.info()
            await SceneLoadedMessage(info=info).send(websocket)
        except Exception as exc:  # pragma: no cover - requires websocket session
            LOGGER.exception("Failed to load USD scene from %s", message.path)
            await ErrorEventMessage(message="Unable to open scene", detail=str(exc)).send(websocket)
