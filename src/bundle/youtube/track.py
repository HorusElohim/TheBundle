import hashlib
import re
from pathlib import Path

from ..core import data


def sanitize_string(input_string: str) -> str:
    invalid_chars = r'[<>:"/\\|?*\0\n\r&]'
    sanitized_string = re.sub(invalid_chars, "", input_string)
    sanitized_string = sanitized_string.replace("  ", " ")
    return sanitized_string


def get_identifier(filename: str) -> str:
    return hashlib.sha256(filename.encode("utf-8")).hexdigest()


class TrackData(data.Data):
    title: str = data.Field(default_factory=str)
    author: str = data.Field(default_factory=str)
    duration: int = data.Field(default_factory=int)
    identifier: str = data.Field(default_factory=str)
    filename: str = data.Field(default_factory=str)

    @data.model_validator(mode="after")
    def post_init(cls, instance):
        instance.author = sanitize_string(instance.author)
        instance.title = sanitize_string(instance.title)
        instance.filename = f"{instance.author}-{instance.title}"
        instance.identifier = get_identifier(instance.filename)
        return instance


class YoutubeTrackData(TrackData):
    audio_url: str = data.Field(default_factory=str)
    video_url: str = data.Field(default_factory=str)
    thumbnail_url: str = data.Field(default_factory=str)

    def is_resolved(self) -> bool:
        """Return True when the resolver filled the stream URLs."""
        return bool(self.video_url.strip())


class MP3TrackData(TrackData):
    path: Path


class MP4TrackData(TrackData):
    path: Path
