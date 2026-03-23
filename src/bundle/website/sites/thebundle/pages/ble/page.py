# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""BLE dashboard routes and websocket scan streaming."""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from bundle import ble
from bundle.website.core.templating import PageModule, base_context

page = PageModule(
    __file__,
    name="BLE",
    description="Scan, inspect, and connect to Nordic UART devices in real time.",
)
_manager: ble.Manager | None = None

REFRESH_INTERVAL_MIN = 1.0
REFRESH_INTERVAL_MAX = 30.0


def _get_manager() -> ble.Manager:
    """Create BLE manager lazily to avoid hardware setup at module import time."""
    global _manager
    if _manager is None:
        _manager = ble.Manager()
    return _manager


@page.router.get("/ble", response_class=HTMLResponse)
async def ble_dashboard(request: Request):
    """Render the BLE dashboard page."""
    return page.templates.TemplateResponse(request, "index.html", base_context(request))


@page.router.get("/ble/api/devices", response_class=JSONResponse)
async def ble_scan(timeout: float = ble.DEFAULT_SCAN_TIMEOUT) -> dict:
    """Run a single BLE scan and return devices as JSON."""
    scan = await _collect_scan(timeout)
    return await scan.as_dict()


@page.router.websocket("/ble/ws/scan")
async def ble_scan_stream(websocket: WebSocket):
    """Continuously scan BLE devices and stream updates to the browser."""
    await websocket.accept()

    refresh_interval = ble.DEFAULT_SCAN_TIMEOUT
    stop_event = asyncio.Event()

    async def scan_loop() -> None:
        nonlocal refresh_interval
        manager = _get_manager()
        while not stop_event.is_set():
            try:
                scan_timeout = min(refresh_interval, ble.DEFAULT_SCAN_TIMEOUT)
                scan = await manager.scan(timeout=scan_timeout)
                payload = await scan.as_dict()
                await websocket.send_json({"type": "scan", "data": payload})
            except RuntimeError as exc:
                # Connection already closed by client or ASGI server.
                if "Unexpected ASGI message 'websocket.send'" in str(exc):
                    stop_event.set()
                    break
                raise
            except asyncio.CancelledError:
                stop_event.set()
                break
            except WebSocketDisconnect:
                stop_event.set()
                break
            except Exception as exc:  # pragma: no cover - defensive logging for BLE hw
                page.logger.error("BLE scan failed during websocket stream: %s", exc)
                try:
                    await websocket.send_json({"type": "error", "message": "BLE scan unavailable"})
                except (RuntimeError, WebSocketDisconnect):
                    stop_event.set()
                    break

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
            page.logger.warning("BLE websocket config error: %s", exc)
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
    """Wrap manager scan to convert hardware/runtime failures into HTTP 503."""
    try:
        return await _get_manager().scan(timeout=timeout)
    except Exception as exc:  # pragma: no cover - BLE hardware errors logged for UI feedback
        page.logger.error("BLE scan failed: %s", exc)
        raise HTTPException(status_code=503, detail="BLE scan unavailable") from exc


def _clamp_interval(value: float) -> float:
    """Clamp client-provided refresh interval into allowed bounds."""
    return max(REFRESH_INTERVAL_MIN, min(value, REFRESH_INTERVAL_MAX))
