"""BLE device snapshot models shared across the scanner."""

from __future__ import annotations

from bleak import uuids as uuid_utils
from bleak.backends.device import BLEDevice as BleakPeripheral
from bleak.backends.scanner import AdvertisementData

from bundle.core import Entity, data

from .vendors import lookup_company

__all__ = ["Advertisement", "Device"]


def _friendly_uuid(uuid: str) -> str:
    try:
        return uuid_utils.uuidstr_to_str(uuid)
    except Exception:  # pragma: no cover - best effort helper
        return uuid


class Advertisement(data.Data):
    """Bleak advertisement adapter with convenience helpers."""

    raw: AdvertisementData | None = data.Field(default=None, repr=False, exclude=True)

    def _raw_attr(self, attr: str):
        return getattr(self.raw, attr, None) if self.raw else None

    @property
    def local_name(self) -> str | None:
        return self._raw_attr("local_name")

    @property
    def rssi(self) -> int | None:
        return self._raw_attr("rssi")

    @property
    def tx_power(self) -> int | None:
        return self._raw_attr("tx_power")

    @property
    def manufacturer_data(self) -> dict[int, bytes]:
        data = self._raw_attr("manufacturer_data")
        return dict(data or {})

    @property
    def manufacturer_id(self) -> int | None:
        data = self.manufacturer_data
        return next(iter(data)) if data else None

    @property
    def manufacturer_label(self) -> str | None:
        company_id = self.manufacturer_id
        if company_id is None:
            return None
        return lookup_company(company_id) or f"0x{company_id:04X}"

    @property
    def service_uuids(self) -> list[str]:
        uuids = self._raw_attr("service_uuids")
        return list(uuids or [])

    @property
    def service_labels(self) -> list[str]:
        return [_friendly_uuid(uuid) for uuid in self.service_uuids]

    def info_fragments(self, *, limit: int = 3) -> list[str]:
        fragments: list[str] = []
        if name := self.local_name:
            fragments.append(f"LocalName={name}")
        if label := self.manufacturer_label:
            fragments.append(f"Manufacturer={label}")
        if services := self.service_labels:
            summary = ", ".join(services[:limit])
            if len(services) > limit:
                summary += f" +{len(services) - limit}"
            fragments.append(f"Services={summary}")
        if self.tx_power is not None:
            fragments.append(f"Tx={self.tx_power} dBm")
        return fragments


class Device(Entity):
    """Entity describing a discovered peripheral."""

    name: str = data.Field(default="<unknown>")
    alias: str | None = data.Field(default=None)
    address: str = data.Field(default="")
    signal: int | None = data.Field(default=None)
    type: str = data.Field(default="BLE device")
    manufacturer: str | None = data.Field(default=None)
    services: list[str] = data.Field(default_factory=list)
    tx_power: int | None = data.Field(default=None)
    local_name: str | None = data.Field(default=None)

    _backend: BleakPeripheral | None = data.PrivateAttr(default=None)
    _advertisement: Advertisement | None = data.PrivateAttr(default=None)

    @classmethod
    def from_backend(cls, device: BleakPeripheral, advertisement: AdvertisementData | None) -> Device:
        adv = Advertisement(raw=advertisement)
        name, alias = cls._names(device, adv)
        services = adv.service_labels
        manufacturer = adv.manufacturer_label
        signal = adv.rssi
        type_label = manufacturer or (services[0] if services else "BLE device")
        instance = cls(
            name=name,
            alias=alias,
            address=device.address,
            signal=signal,
            type=type_label,
            manufacturer=manufacturer,
            services=services,
            tx_power=adv.tx_power,
            local_name=adv.local_name,
        )
        instance._backend = device
        instance._advertisement = adv
        return instance

    @staticmethod
    def _names(device: BleakPeripheral, adv: Advertisement) -> tuple[str, str | None]:
        display = next(filter(None, (device.name, adv.local_name, "<unknown>")))
        alias = adv.local_name if adv.local_name and adv.local_name != display else None
        return display, alias

    @property
    def raw_device(self) -> BleakPeripheral | None:
        return self._backend

    @property
    def rssi_display(self) -> str:
        return str(self.signal) if self.signal is not None else "?"

    @property
    def info_line(self) -> str:
        extras = self._advertisement.info_fragments() if self._advertisement else []
        summary = f"{self.name} [{self.address}] RSSI={self.rssi_display}"
        return f"{summary} ({'; '.join(extras)})" if extras else summary

    def matches_name(self, query: str) -> bool:
        if not query:
            return False
        query = query.lower()
        candidates = (candidate.lower() for candidate in (self.name, self.alias, self.local_name) if candidate)
        return any(query in candidate for candidate in candidates)

    def __str__(self) -> str:  # pragma: no cover - convenience for printing
        return self.info_line
