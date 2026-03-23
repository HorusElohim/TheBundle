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

"""High-level helpers for BLE discovery and presentation."""

from __future__ import annotations

from collections.abc import Iterator

from bleak import BleakScanner
from bleak.backends.device import BLEDevice as BleakPeripheral
from bleak.backends.scanner import AdvertisementData

from bundle.core import Entity, data, logger, tracer

from .device import Device

log = logger.get_logger(__name__)

DEFAULT_SCAN_TIMEOUT = 5.0


class ScanResult(data.Data):
    """Entity describing a scan run and its collected devices."""

    timeout: float = data.Field(default=DEFAULT_SCAN_TIMEOUT)
    devices: list[Device] = data.Field(default_factory=list)

    def sorted_devices(self) -> list[Device]:
        return sorted(
            self.devices,
            key=lambda device: device.signal if device.signal is not None else -200,
            reverse=True,
        )

    def lines(self) -> list[str]:
        return [device.info_line for device in self.sorted_devices()]


class Scanner(Entity):
    """Collect advertisement snapshots from nearby peripherals."""

    timeout: float = data.Field(default=DEFAULT_SCAN_TIMEOUT)

    @tracer.Async.decorator.call_raise
    async def scan(self, *, timeout: float | None = None) -> ScanResult:
        limit = timeout if timeout is not None else self.timeout
        log.debug("BLE scan timeout=%s", limit)
        raw_results = await BleakScanner.discover(timeout=limit, return_adv=True)
        devices = [
            Device.from_backend(device, advertisement)
            for device, advertisement in _iter_results(raw_results)
        ]
        return ScanResult(timeout=limit, devices=devices)


def _iter_results(
    raw_results: object,
) -> Iterator[tuple[BleakPeripheral, AdvertisementData | None]]:
    if isinstance(raw_results, dict):
        yield from raw_results.values()
        return
    for device in raw_results or []:
        yield device, None


@tracer.Async.decorator.call_raise
async def discover(*, timeout: float = DEFAULT_SCAN_TIMEOUT) -> list[Device]:
    return (await Scanner(timeout=timeout).scan()).devices
