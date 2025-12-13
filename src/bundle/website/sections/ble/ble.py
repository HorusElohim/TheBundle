from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from bundle import ble

from ...common.sections import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "ble"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)
MANAGER = ble.Manager()

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)

REFRESH_INTERVAL_MIN = 1.0
REFRESH_INTERVAL_MAX = 30.0


@router.get("/ble", response_class=HTMLResponse)
async def ble_dashboard(request: Request):
    return templates.TemplateResponse("index.html", base_context(request))


@router.get("/ble/api/devices", response_class=JSONResponse)
async def ble_scan(timeout: float = ble.DEFAULT_SCAN_TIMEOUT) -> dict:
    scan = await _collect_scan(timeout)
    return await scan.as_dict()


@router.websocket("/ble/ws/scan")
async def ble_scan_stream(websocket: WebSocket):
    await websocket.accept()

    refresh_interval = ble.DEFAULT_SCAN_TIMEOUT
    stop_event = asyncio.Event()

    async def scan_loop() -> None:
        nonlocal refresh_interval
        while not stop_event.is_set():
            try:
                scan_timeout = min(refresh_interval, ble.DEFAULT_SCAN_TIMEOUT)
                scan = await MANAGER.scan(timeout=scan_timeout)
                payload = await scan.as_dict()
                await websocket.send_json({"type": "scan", "data": payload})
            except asyncio.CancelledError:
                stop_event.set()
                break
            except WebSocketDisconnect:
                stop_event.set()
                break
            except Exception as exc:  # pragma: no cover - defensive logging for BLE hw
                LOGGER.error("BLE scan failed during websocket stream: %s", exc)
                await websocket.send_json({"type": "error", "message": "BLE scan unavailable"})

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=refresh_interval)
            except asyncio.TimeoutError:
                continue

    async def control_loop() -> None:
        nonlocal refresh_interval
        try:
            while not stop_event.is_set():
                message = await websocket.receive_json()
                message_type = message.get("type")
                if message_type == "config":
                    interval = float(message.get("interval", refresh_interval))
                    refresh_interval = _clamp_interval(interval)
                elif message_type == "close":
                    stop_event.set()
        except asyncio.CancelledError:
            stop_event.set()
        except WebSocketDisconnect:
            stop_event.set()
        except Exception as exc:  # pragma: no cover - malformed client input
            LOGGER.warning("BLE websocket config error: %s", exc)
            stop_event.set()

    scan_task = asyncio.create_task(scan_loop())
    control_task = asyncio.create_task(control_loop())

    await stop_event.wait()

    for task in (scan_task, control_task):
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    with contextlib.suppress(RuntimeError):
        await websocket.close()


async def _collect_scan(timeout: float) -> ble.ScanResult:
    try:
        return await MANAGER.scan(timeout=timeout)
    except Exception as exc:  # pragma: no cover - BLE hardware errors logged for UI feedback
        LOGGER.error("BLE scan failed: %s", exc)
        raise HTTPException(status_code=503, detail="BLE scan unavailable") from exc


def _clamp_interval(value: float) -> float:
    return max(REFRESH_INTERVAL_MIN, min(value, REFRESH_INTERVAL_MAX))
