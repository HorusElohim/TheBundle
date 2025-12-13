"""Bleak-powered Nordic UART link management."""

from __future__ import annotations

from typing import Callable

from bleak import BleakClient

from bundle.core import Entity, data, logger, tracer

from .framing import FrameCodec
from .scanner import DEFAULT_SCAN_TIMEOUT, Device, Scanner

log = logger.get_logger(__name__)

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


class NordicLink(Entity):
    """High-level helper managing a single Nordic UART Service connection."""

    name: str = data.Field(default="nordic-link")
    device_address: str | None = data.Field(default=None)
    device_name: str | None = data.Field(default=None)
    timeout: float = data.Field(default=DEFAULT_SCAN_TIMEOUT)

    _client: BleakClient | None = data.PrivateAttr(default=None)
    _callback: Callable[[bytes], None] | None = data.PrivateAttr(default=None)
    _codec: FrameCodec = data.PrivateAttr(default_factory=FrameCodec)
    _scanner: Scanner = data.PrivateAttr()

    def __init__(self, *args, scanner: Scanner | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._scanner = scanner or Scanner(timeout=self.timeout)

    async def __aenter__(self) -> "NordicLink":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - context helper
        await self.disconnect()

    def on_message(self, callback: Callable[[bytes], None]) -> None:
        self._callback = callback

    def _notify(self, _: object, data: bytes) -> None:
        for frame in self._codec.feed(data):
            if not self._callback:
                log.debug("NordicLink dropped data without registered callback")
                continue
            try:
                self._callback(frame)
            except Exception:  # pragma: no cover - defensive logging
                log.exception("NordicLink callback raised an exception")

    @property
    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected)

    @tracer.Async.decorator.call_raise
    async def connect(self) -> None:
        if self.is_connected:
            log.debug("NordicLink.connect() called while already connected")
            return

        client = await self._build_client()
        await client.connect()
        if not client.is_connected:
            await client.disconnect()
            raise RuntimeError("Failed to connect to BLE device")

        log.info("Connected to BLE device %s", client.address)
        await client.get_services()
        if SERVICE_UUID not in client.services:
            log.warning("Nordic UART Service %s not found on device", SERVICE_UUID)
        await client.start_notify(TX_CHAR_UUID, self._notify)
        self._client = client

    @tracer.Async.decorator.call_raise
    async def disconnect(self) -> None:
        if not self._client:
            log.debug("NordicLink.disconnect() called without active client")
            return

        client = self._client
        self._client = None
        self._codec = FrameCodec()

        if client.is_connected:
            log.info("Disconnecting BLE device %s", client.address)
            await client.stop_notify(TX_CHAR_UUID)
            await client.disconnect()
        else:
            log.debug("Bleak client already disconnected")

    @tracer.Async.decorator.call_raise
    async def send(self, payload: bytes) -> None:
        if not self._client or not self._client.is_connected:
            raise RuntimeError("Cannot write without an active BLE connection")

        log.debug("NordicLink.send() bytes=%s", len(payload))
        for frame in self._codec.encode(payload):
            await self._client.write_gatt_char(RX_CHAR_UUID, frame, response=True)

    async def _build_client(self) -> BleakClient:
        if self.device_address:
            log.info("Connecting to BLE device at address %s", self.device_address)
            return BleakClient(self.device_address)

        if not self.device_name:
            raise RuntimeError("device_name or device_address must be provided")

        device = await self._discover_device(self.device_name)
        raw = device.raw_device
        if not raw:
            raise RuntimeError("Discovered device missing backend reference")
        log.info("Connecting to BLE device %s [%s]", device.name, device.address)
        return BleakClient(raw)

    async def _discover_device(self, name: str) -> Device:
        log.info("Scanning for BLE devices matching '%s'", name)
        scan = await self._scanner.scan(timeout=self.timeout)
        for device in scan.devices:
            if device.matches_name(name):
                log.info("Found device '%s' [%s]", device.name, device.address)
                return device
        raise RuntimeError(f"BLE device with name containing '{name}' not found")
