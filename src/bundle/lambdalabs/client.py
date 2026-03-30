"""Lambda Labs REST API client."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from bundle.core import logger

from .models import Instance, InstanceSpecs, InstanceType, LaunchRequest, SshKey

log = logger.get_logger(__name__)

BASE_URL = "https://cloud.lambdalabs.com/api/v1"
DEFAULT_POLL_INTERVAL = 10  # seconds


class LambdaApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Lambda API error {status_code}: {message}")


class LambdaClient:
    """Async client for the Lambda Labs Cloud API v1.

    Usage:
        async with LambdaClient(api_key="...") as client:
            types = await client.instance_types()
            instance = await client.launch("gpu_1x_a10", ssh_key_names=["mykey"])
            await client.wait_active(instance.id)
            await client.terminate([instance.id])
    """

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> LambdaClient:
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            auth=(self._api_key, ""),
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *_) -> None:
        if self._http:
            await self._http.aclose()

    def _check(self, resp: httpx.Response) -> dict:
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                msg = resp.text
            raise LambdaApiError(resp.status_code, msg)
        return resp.json()

    async def instance_types(self) -> dict[str, InstanceType]:
        """Return available instance types keyed by name."""
        resp = await self._http.get("/instance-types")
        data = self._check(resp)
        result = {}
        for name, info in data.get("data", {}).items():
            specs_raw = info.get("instance_type", {}).get("specs", {})
            specs = InstanceSpecs(
                vcpus=specs_raw.get("vcpus", 0),
                memory_gib=specs_raw.get("memory_gib", 0),
                storage_gib=specs_raw.get("storage_gib", 0),
            )
            it = info.get("instance_type", {})
            result[name] = InstanceType(
                name=name,
                description=it.get("description", ""),
                price_cents_per_hour=it.get("price_cents_per_hour", 0),
                specs=specs,
            )
        return result

    async def instances(self) -> list[Instance]:
        """Return all active instances."""
        resp = await self._http.get("/instances")
        data = self._check(resp)
        return [self._parse_instance(i) for i in data.get("data", [])]

    async def get_instance(self, instance_id: str) -> Instance:
        """Return a single instance by ID."""
        resp = await self._http.get(f"/instances/{instance_id}")
        data = self._check(resp)
        return self._parse_instance(data["data"])

    async def launch(
        self,
        instance_type_name: str,
        ssh_key_names: list[str],
        region_name: str = "us-east-1",
        name: str | None = None,
        quantity: int = 1,
    ) -> list[str]:
        """Launch instances. Returns list of instance IDs."""
        req = LaunchRequest(
            region_name=region_name,
            instance_type_name=instance_type_name,
            ssh_key_names=ssh_key_names,
            name=name,
            quantity=quantity,
        )
        resp = await self._http.post(
            "/instance-operations/launch",
            json=req.model_dump(exclude_none=True),
        )
        data = self._check(resp)
        return data.get("data", {}).get("instance_ids", [])

    async def terminate(self, instance_ids: list[str]) -> list[str]:
        """Terminate instances. Returns list of terminated instance IDs."""
        resp = await self._http.post(
            "/instance-operations/terminate",
            json={"instance_ids": instance_ids},
        )
        data = self._check(resp)
        return data.get("data", {}).get("terminated_instances", [])

    async def ssh_keys(self) -> list[SshKey]:
        """Return all SSH keys in the account."""
        resp = await self._http.get("/ssh-keys")
        data = self._check(resp)
        return [SshKey(id=k["id"], name=k["name"], public_key=k["public_key"]) for k in data.get("data", [])]

    async def add_ssh_key(self, name: str, public_key: str) -> SshKey:
        """Add an SSH key to the account."""
        resp = await self._http.post(
            "/ssh-keys",
            json={"name": name, "public_key": public_key},
        )
        data = self._check(resp)
        k = data["data"]
        return SshKey(id=k["id"], name=k["name"], public_key=k["public_key"])

    async def delete_ssh_key(self, key_id: str) -> None:
        """Delete an SSH key by ID."""
        resp = await self._http.delete(f"/ssh-keys/{key_id}")
        self._check(resp)

    async def wait_active(
        self,
        instance_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = 600,
    ) -> Instance:
        """Poll until the instance is active with an IP. Raises TimeoutError on timeout."""
        elapsed = 0.0
        while elapsed < timeout:
            instance = await self.get_instance(instance_id)
            log.info("Instance %s status: %s (ip: %s)", instance_id[:8], instance.status.value, instance.ip or "—")
            if instance.is_ready:
                return instance
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(f"Instance {instance_id} did not become active within {timeout}s")

    @staticmethod
    def _parse_instance(raw: dict) -> Instance:
        it_raw = raw.get("instance_type", {})
        specs_raw = it_raw.get("specs", {})
        instance_type = InstanceType(
            name=it_raw.get("name", ""),
            description=it_raw.get("description", ""),
            price_cents_per_hour=it_raw.get("price_cents_per_hour", 0),
            specs=InstanceSpecs(
                vcpus=specs_raw.get("vcpus", 0),
                memory_gib=specs_raw.get("memory_gib", 0),
                storage_gib=specs_raw.get("storage_gib", 0),
            ),
        )
        return Instance(
            id=raw["id"],
            name=raw.get("name"),
            status=raw.get("status", "booting"),
            instance_type=instance_type,
            ip=raw.get("ip"),
            region=raw.get("region", {}),
            ssh_key_names=raw.get("ssh_key_names", []),
            file_system_names=raw.get("file_system_names", []),
        )
