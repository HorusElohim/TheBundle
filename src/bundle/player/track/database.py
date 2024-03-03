from __future__ import annotations

from pathlib import Path
from bundle.core import data, atom
from PySide6.QtCore import QUrl
from threading import Lock

from .base import TrackBase

LOCK = Lock()


class TrackDatabase(atom.Atom):
    database: dict[str, Path] = data.Field(default_factory=dict)

    def has(self, track: TrackBase):
        with LOCK:
            return track.identifier in self.database

    def add(self, track: TrackBase):
        with LOCK:
            track_path = Path(track.path.toString()) if isinstance(track.path, QUrl) else Path(track.path)
            self.database[track.identifier] = track_path

    def get(self, identifier: str) -> Path:
        with LOCK:
            return self.database[identifier]


DB = TrackDatabase()
