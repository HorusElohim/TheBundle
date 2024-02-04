from __future__ import annotations
import bundle
from PySide6.QtCore import QUrl
from threading import Lock

from ..config import DATA_PATH
from .base import TrackBase

LOCK = Lock()


@bundle.Data.dataclass
class TrackDatabase(bundle.Entity):
    database: dict[str : bundle.Path] = bundle.Entity.field(default_factory=dict)

    def has(self, track: TrackBase):
        with LOCK:
            return track.identifier in self.database

    def add(self, track: TrackBase):
        with LOCK:
            track_path = bundle.Path(track.path.toString()) if isinstance(track.path, QUrl) else bundle.Path(track.path)
            self.database[track.identifier] = track_path

    def get(self, identifier: str) -> bundle.Path:
        with LOCK:
            return self.database[identifier]


DB = TrackDatabase()
