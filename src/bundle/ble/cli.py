"""Bundle BLE subcommand for the project CLI."""

from __future__ import annotations

import asyncio

import rich_click as click

from bundle.core import logger, tracer

from .manager import Manager

log = logger.get_logger(__name__)


async def _interactive_session(name: str | None, address: str | None) -> None:
    manager = Manager()
    link = await manager.open(device_name=name, device_address=address)

    def on_frame(data: bytes) -> None:
        log.info("RX %s", data.hex())
        click.echo(f"< {data.decode('utf-8', errors='replace')}")

    link.on_message(on_frame)

    async with link:
        try:
            while True:
                try:
                    line = await asyncio.to_thread(input, "> ")
                except EOFError:
                    break
                if not line:
                    continue
                await link.send(line.encode("utf-8"))
        except KeyboardInterrupt:
            log.info("Keyboard interrupt received, disconnecting")


@click.group()
@tracer.Sync.decorator.call_raise
async def ble() -> None:
    """Interact with Bundle's BLE module."""


@ble.command()
@click.option("--timeout", type=float, default=5.0, show_default=True, help="Seconds to scan")
@tracer.Sync.decorator.call_raise
async def scan(timeout: float) -> None:
    """Scan for available BLE devices."""

    manager = Manager()
    result = await manager.scan(timeout=timeout)
    if not result.devices:
        click.echo("No BLE devices found")
        return
    for device in result.lines():
        log.info("%s", device)


@ble.command()
@click.option("--name", help="Connect to the first device containing this name substring")
@click.option("--address", help="Connect to the device with this BLE address")
@tracer.Sync.decorator.call_raise
async def connect(name: str | None, address: str | None) -> None:
    """Open an interactive BLE console using NUS."""

    if not name and not address:
        raise click.UsageError("Specify --name or --address to connect to a device")

    await _interactive_session(name, address)
