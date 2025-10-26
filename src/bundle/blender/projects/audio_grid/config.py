"""Configuration model for the audio grid project."""

from __future__ import annotations

from pathlib import Path

from bundle.core import data, logger, tracer

log = logger.get_logger(__name__)

_DEFAULT_CONFIG = Path(__file__).with_name("default_config.json")


class AudioGridConfig(data.Data):
    """Validated configuration for driving the audio grid scene."""

    audio: Path = data.Field(default_factory=Path)
    object_name: str | None = data.Field(default=None, alias="object")
    frames: str | int = "auto"
    fps: int | None = None
    amp_scale: float = 5.0
    normalize: float = 0.98
    smooth: int = 0

    _base_dir: Path = data.PrivateAttr(default=_DEFAULT_CONFIG.parent)

    @property
    def frame_count(self) -> int | None:
        if isinstance(self.frames, str) and self.frames.lower() == "auto":
            return None
        return int(self.frames)

    @tracer.Async.decorator.call_raise
    @classmethod
    async def load(cls, path: str | Path | None = None) -> AudioGridConfig:
        target = Path(path) if path else _DEFAULT_CONFIG
        log.info("Loading audio grid config from %s", target)
        config = await cls.from_json(target)
        config._base_dir = target.parent
        return config

    def resolved_audio_path(self) -> Path:
        audio_path = Path(self.audio)
        if not audio_path.is_absolute():
            audio_path = (self._base_dir / audio_path).resolve()
        return audio_path