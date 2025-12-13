"""Bluetooth SIG company identifier helpers."""

from __future__ import annotations

from pathlib import Path

import yaml

from bundle.core import data

__all__ = ["lookup_company"]

_DATA_DIR = Path(__file__).with_name("data")
COMPANY_FILE = _DATA_DIR.joinpath("company_identifiers.yaml")


class CompanyEntry(data.Data):
    """Single Assigned Number entry provided by the SIG."""

    identifier: int = data.Field(alias="value")
    name: str

    @data.field_validator("identifier", mode="before")
    @classmethod
    def _coerce_identifier(cls, value: int | str) -> int:
        if isinstance(value, int):
            return value
        text = value.strip()
        base = 16 if text.lower().startswith("0x") else 10
        return int(text, base)


class CompanyCatalog(data.Data):
    """Lookup table for Bluetooth SIG company identifiers."""

    company_identifiers: list[CompanyEntry] = data.Field(default_factory=list)
    _mapping: dict[int, str] = data.PrivateAttr(default_factory=dict)

    @data.model_validator(mode="after")
    def _initialize_mapping(self) -> "CompanyCatalog":
        self._mapping = {entry.identifier: entry.name for entry in self.company_identifiers}
        return self

    @classmethod
    def from_resource(cls, path: Path | None = None) -> "CompanyCatalog":
        resource = path or COMPANY_FILE
        content = yaml.safe_load(resource.read_text(encoding="utf-8"))
        return cls(**content)

    def lookup(self, company_id: int | None) -> str | None:
        if company_id is None:
            return None
        return self._mapping.get(company_id)


_COMPANIES = CompanyCatalog.from_resource()


def lookup_company(company_id: int | None) -> str | None:
    """Return the vendor label for ``company_id`` if it exists."""

    return _COMPANIES.lookup(company_id)
