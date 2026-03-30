"""Lambda Labs local config — API key and SSH key preference."""

from __future__ import annotations

import json
from pathlib import Path

from bundle.core.data import Data

CONFIG_PATH = Path.home() / ".bundle" / "lambdalabs.json"


class LambdaLabsConfig(Data):
    api_key: str = ""
    default_ssh_key: str = ""
    default_region: str = "us-east-1"
    default_instance_type: str = "gpu_1x_a10"

    @classmethod
    def load(cls) -> LambdaLabsConfig:
        if CONFIG_PATH.exists():
            return cls.model_validate(json.loads(CONFIG_PATH.read_text()))
        return cls()

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self.model_dump(), indent=2))

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
