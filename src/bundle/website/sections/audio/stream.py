from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from bundle.core import logger

from bundle.audio.engine import apply_transforms, get_waveform, load_audio
from bundle.audio.models import AudioState, AudioTransform, AudioView
from bundle.audio.protocol import AudioMessageType, PROTOCOL_VERSION, build_envelope


class AudioStream:
    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.state: AudioState | None = None
        self.log = logger.get_logger(__name__)

    async def send_error(self, message: str) -> None:
        self.log.error("AudioStream error: %s", message)
        await self.websocket.send_json(build_envelope(AudioMessageType.ERROR, {"message": message}))

    async def send_state(self) -> None:
        if self.state:
            self.log.debug(
                "AudioStream state: source=%s zoom=%s offset=%s selection=%s transforms=%s",
                self.state.source.path,
                self.state.view.zoom,
                self.state.view.offset_sec,
                self.state.view.selection,
                len(self.state.transforms),
            )
            await self.websocket.send_json(
                build_envelope(AudioMessageType.STATE, self.state.model_dump(mode="json"))
            )

    async def send_waveform(self) -> None:
        if not self.state:
            return
        samples = get_waveform(
            source=self.state.source,
            zoom=self.state.view.zoom,
            offset=self.state.view.offset_sec,
        )
        processed = apply_transforms(samples, self.state.transforms)
        self.log.debug(
            "AudioStream waveform: samples=%s processed=%s offset=%s zoom=%s",
            len(samples),
            len(processed),
            self.state.view.offset_sec,
            self.state.view.zoom,
        )
        await self.websocket.send_json(
            build_envelope(
                AudioMessageType.WAVEFORM_CHUNK,
                {
                    "samples": processed.tolist(),
                    "start": self.state.view.offset_sec,
                },
            )
        )

    async def handle_message(self, message: dict[str, Any]) -> None:
        version = message.get("v")
        if version != PROTOCOL_VERSION:
            await self.send_error("Unsupported protocol version")
            return

        message_type = message.get("type")
        if isinstance(message_type, AudioMessageType):
            message_type = message_type.value
        payload = message.get("payload") or {}
        self.log.debug("AudioStream message: type=%s payload_keys=%s", message_type, list(payload.keys()))

        match message_type:
            case AudioMessageType.LOAD.value:
                await self._handle_load(payload)
            case AudioMessageType.VIEW_SET.value:
                await self._handle_view(payload)
            case AudioMessageType.SELECT.value:
                await self._handle_select(payload)
            case AudioMessageType.TRANSFORM_ADD.value:
                await self._handle_transform_add(payload)
            case AudioMessageType.TRANSFORM_CLEAR.value:
                await self._handle_transform_clear()
            case _:
                await self.send_error(f"Unknown message type: {message_type}")

    async def _handle_load(self, payload: dict[str, Any]) -> None:
        path = payload.get("path")
        if not path:
            await self.send_error("Missing 'path' in audio.load")
            return
        try:
            self.log.info("AudioStream load: path=%s", path)
            source = load_audio(path)
        except Exception as exc:  # noqa: BLE001
            await self.send_error(str(exc))
            return

        view = AudioView(zoom=512.0, offset_sec=0.0, selection=None)
        self.state = AudioState(source=source, view=view, transforms=[])
        await self.send_state()
        await self.send_waveform()

    async def _handle_view(self, payload: dict[str, Any]) -> None:
        if not self.state:
            await self.send_error("Audio not loaded")
            return

        zoom = float(payload.get("zoom", self.state.view.zoom))
        offset_sec = float(payload.get("offset_sec", self.state.view.offset_sec))
        self.log.debug("AudioStream view: zoom=%s offset=%s", zoom, offset_sec)
        self.state = self.state.model_copy(
            update={"view": AudioView(zoom=zoom, offset_sec=offset_sec, selection=self.state.view.selection)}
        )
        await self.send_state()
        await self.send_waveform()

    async def _handle_select(self, payload: dict[str, Any]) -> None:
        if not self.state:
            await self.send_error("Audio not loaded")
            return
        start = float(payload.get("start", 0))
        end = float(payload.get("end", start))
        selection = (min(start, end), max(start, end))
        self.log.debug("AudioStream selection: start=%s end=%s", selection[0], selection[1])
        view = self.state.view.model_copy(update={"selection": selection})
        self.state = self.state.model_copy(update={"view": view})
        await self.send_state()

    async def _handle_transform_add(self, payload: dict[str, Any]) -> None:
        if not self.state:
            await self.send_error("Audio not loaded")
            return
        transform_payload = payload.get("transform")
        if not isinstance(transform_payload, dict):
            await self.send_error("Invalid transform payload")
            return
        self.log.debug("AudioStream transform add: %s", transform_payload)
        transform = AudioTransform(**transform_payload)
        self.state = self.state.model_copy(update={"transforms": [*self.state.transforms, transform]})
        await self.send_state()
        await self.send_waveform()

    async def _handle_transform_clear(self) -> None:
        if not self.state:
            await self.send_error("Audio not loaded")
            return
        self.log.debug("AudioStream transform clear")
        self.state = self.state.model_copy(update={"transforms": []})
        await self.send_state()
        await self.send_waveform()

    async def run(self) -> None:
        await self.websocket.accept()
        self.log.info("AudioStream connected")
        try:
            while True:
                try:
                    message = await self.websocket.receive_json()
                except WebSocketDisconnect:
                    break
                await self.handle_message(message)
        finally:
            self.log.info("AudioStream disconnected")
            await asyncio.sleep(0)


def create_stream(websocket: WebSocket) -> AudioStream:
    return AudioStream(websocket)
