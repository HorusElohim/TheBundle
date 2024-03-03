import asyncio
import os
from pathlib import Path

from ..core import data
from . import LOGGER
from .media import MP3, MP4


class Database(data.Data):
    path: Path
    tracks: dict[str, MP3 | MP4] = data.Field(default_factory=dict)

    async def load(self):
        tasks = []
        for root, _, files in os.walk(self.path):
            for file in files:
                full_path = Path(root) / file
                if file.endswith(".mp4"):
                    tasks.append(MP4.load(full_path))
                elif file.endswith(".mp3"):
                    tasks.append(MP3.load(full_path))
        loaded_tracks = filter(None, await asyncio.gather(*tasks))
        for track in loaded_tracks:
            self.tracks[track.identifier] = track
        LOGGER.debug(f"load complete - {len(self.tracks)}")

    def _has(self, identifier):
        return identifier in self.tracks

    async def has(self, identifier):
        return await asyncio.to_thread(self._has, identifier)

    def _add(self, track: MP4 | MP3):
        if not self._has(track.identifier):
            self.tracks[track.identifier] = track

    async def add(self, track: MP4 | MP3):
        return await asyncio.to_thread(self._add, track)
