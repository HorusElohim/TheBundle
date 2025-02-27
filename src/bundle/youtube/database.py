import asyncio
import os
from pathlib import Path

from ..core import data, logger, tracer
from .media import MP3, MP4

log = logger.get_logger(__name__)


class Database(data.Data):
    path: Path
    tracks: dict[str, MP3 | MP4] = data.Field(default_factory=dict)

    @tracer.Async.decorator.call_raise
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
        log.debug(f"load complete - {len(self.tracks)}")

    @tracer.Sync.decorator.call_raise
    def has(self, identifier):
        return identifier in self.tracks

    @tracer.Sync.decorator.call_raise
    def add(self, track: MP4 | MP3):
        assert isinstance(track, MP4 | MP3), f"received: {type(track)}"
        if not self.has(track.identifier):
            self.tracks[track.identifier] = track
