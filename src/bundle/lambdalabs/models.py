"""Lambda Labs API data models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from bundle.core.data import Data


class InstanceStatus(str, Enum):
    BOOTING = "booting"
    ACTIVE = "active"
    UNHEALTHY = "unhealthy"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


class InstanceSpecs(Data):
    vcpus: int
    memory_gib: int
    storage_gib: int


class InstanceType(Data):
    name: str
    description: str
    price_cents_per_hour: int
    specs: InstanceSpecs

    @property
    def price_per_hour(self) -> float:
        return self.price_cents_per_hour / 100


class Instance(Data):
    id: str
    name: str | None = None
    status: InstanceStatus
    instance_type: InstanceType
    ip: str | None = None
    region: dict[str, Any] = {}
    ssh_key_names: list[str] = []
    file_system_names: list[str] = []

    @property
    def is_active(self) -> bool:
        return self.status == InstanceStatus.ACTIVE

    @property
    def is_ready(self) -> bool:
        return self.status == InstanceStatus.ACTIVE and bool(self.ip)


class SshKey(Data):
    id: str
    name: str
    public_key: str


class LaunchRequest(Data):
    region_name: str
    instance_type_name: str
    ssh_key_names: list[str]
    name: str | None = None
    quantity: int = 1
    file_system_names: list[str] = []
