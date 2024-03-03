from bundle import data, logger
from pathlib import Path
from logging import getLogger
from PySide6.QtCore import QUrl
from .base import TrackBase
from ..medias import MP3, MP4


log = getLogger(__name__)


class TrackLocalConfig(data.ConfigDict):
    arbitrary_types_allowed: bool = True
    from_attributes: bool = True
    json_encoders = {
        Path: lambda v: str(v),
    }


class TrackLocal(TrackBase):
    path: Path | None = data.Field(default=None)

    __config__ = TrackLocalConfig

    @data.model_validator(mode="after")
    def post_init(self):
        match self.path.suffix:
            case ".mp3":
                self.track = MP3.load(self.path)
            case ".mp4":
                self.track = MP4.load(self.path)
            case _:
                self.track = None
        log.debug(f"constructed {logger.Emoji.success}")

    @data.field_validator("path")
    def validate_path(cls, value):
        if value is None:
            raise ValueError("path cannot be None")
        if isinstance(value, str):
            return Path(value)
        return value

    @property
    def filename(self) -> str:
        match self.path:
            case Path():
                return self.path.name
            case QUrl():
                return self.path.fileName()
            case _:
                return ""
