"""High-level entry point coordinating BLE scans and connections."""

from __future__ import annotations

import asyncio

from bundle.core import Entity, data, logger, tracer

from .link import NordicLink
from .scanner import DEFAULT_SCAN_TIMEOUT, Scanner, ScanResult

log = logger.get_logger(__name__)


class Manager(Entity):
    """Provide a compact API for scanning and opening Nordic UART links."""

    name: str = data.Field(default="ble-manager")
    default_timeout: float = data.Field(default=DEFAULT_SCAN_TIMEOUT)

    _scanner: Scanner = data.PrivateAttr()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._scanner = Scanner(timeout=self.default_timeout)

    @tracer.Async.decorator.call_raise
    async def scan(self, *, timeout: float | None = None) -> ScanResult:
        limit = timeout if timeout is not None else self.default_timeout
        log.debug("Manager.scan() timeout=%s", limit)
        scanner = self._scanner if timeout is None else Scanner(timeout=limit)
        try:
            return await scanner.scan(timeout=limit)
        except asyncio.CancelledError:
            log.debug("Manager.scan() cancelled, returning empty scan result")
            return ScanResult(timeout=limit, devices=[])

    @tracer.Async.decorator.call_raise
    async def open(
        self,
        *,
        device_name: str | None = None,
        device_address: str | None = None,
        timeout: float | None = None,
    ) -> NordicLink:
        if not device_name and not device_address:
            raise RuntimeError("device_name or device_address must be provided")

        limit = timeout if timeout is not None else self.default_timeout
        scanner = self._scanner if timeout is None else Scanner(timeout=limit)
        link = NordicLink(
            device_name=device_name,
            device_address=device_address,
            timeout=limit,
            scanner=scanner,
        )
        await link.connect()
        return link
