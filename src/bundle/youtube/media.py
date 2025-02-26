# Copyright 2024 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

from pathlib import Path
from typing import Type

import ffmpeg
from mutagen.id3 import APIC, ID3, TIT2, TPE1, error
from mutagen.mp3 import MP3 as MutagenMP3
from mutagen.mp4 import MP4 as MutagenMP4
from mutagen.mp4 import MP4Cover

from ..core import tracer
from . import LOGGER
from .data import MP3TrackData, MP4TrackData, TrackData


class MP3(MP3TrackData):
    @classmethod
    def from_track(cls: Type[MP3], path, track: TrackData):
        return cls(path=path, author=track.author, title=track.title, duration=track.duration)

    def _save(self, thumbnail: None | bytes = None):
        mp3 = MutagenMP3(self.path, ID3=ID3)
        # Add ID3 tag if it doesn't exist
        try:
            mp3.add_tags()
        except error:
            pass
        # Set metadata
        mp3.tags.add(TIT2(encoding=3, text=self.title))
        mp3.tags.add(TPE1(encoding=3, text=self.author))

        if thumbnail and len(thumbnail) > 0:
            mp3.tags.add(APIC(encoding=3, mime="image/png", type=3, desc="Cover", data=thumbnail))
        mp3.save()

    async def save(self, thumbnail: None | bytes = None):
        return await tracer.Async.call_raise(self._save, thumbnail)

    def _get_thumbnail(self) -> bytes:
        mp3 = MutagenMP3(self.path, ID3=ID3)
        thumbnail_data = bytes()
        if mp3.tags and "APIC:Cover" in mp3.tags:
            thumbnail_data = mp3.tags["APIC:Cover"].data
        return thumbnail_data

    async def get_thumbnail(self) -> bytes:
        return await tracer.Async.call_raise(self._get_thumbnail)

    @classmethod
    def _load(cls, path: Path) -> MP3:
        mp3 = MutagenMP3(path, ID3=ID3)
        raw_title = mp3.get("TIT2", [None])
        if raw_title:
            title = raw_title[0]
        raw_author = mp3.get("TPE1", [None])
        if raw_author:
            author = raw_author[0]
        duration = int(mp3.info.length)
        return MP3(path=path, title=title, author=author, duration=duration)

    @classmethod
    async def load(cls, path: Path) -> MP3 | None:
        return await tracer.Async.call_raise(cls._load, path)


class MP4(MP4TrackData):
    @classmethod
    def from_track(cls: Type[MP4], path, track: TrackData):
        return cls(path=path, author=track.author, title=track.title, duration=track.duration)

    def _save(self, thumbnail: None | bytes = None):
        mp4 = MutagenMP4(self.path)
        # Set metadata
        mp4["\xa9nam"] = self.title  # Title
        mp4["\xa9ART"] = self.author  # Artist/Author
        if thumbnail and len(thumbnail) > 0:
            # For the cover, MP4Cover expects the image data, and the second argument is the image format
            # MP4Cover.FORMAT_JPEG or MP4Cover.FORMAT_PNG depending on your thumbnail's format
            cover_format = MP4Cover.FORMAT_PNG if thumbnail.startswith(b"\x89PNG") else MP4Cover.FORMAT_JPEG
            mp4["covr"] = [MP4Cover(thumbnail, imageformat=cover_format)]
        mp4.save()

    async def save(self, thumbnail: None | bytes = None):
        return await tracer.Async.call_raise(self._save, thumbnail, log_level=logger.Level.VERBOSE)

    @classmethod
    def _load(cls, path: Path) -> MP4 | None:
        mp4 = MutagenMP4(path)
        # Load metadata
        raw_title = mp4.get("\xa9nam", [None])
        if raw_title:
            title = raw_title[0]
        raw_author = mp4.get("\xa9ART", [None])
        if raw_author:
            author = raw_author[0]

        title = str(title)
        author = str(author)
        duration = int(mp4.info.length)
        return MP4(path=path, title=title, author=author, duration=duration)

    def _get_thumbnail(self) -> bytes | None:
        mp4 = MutagenMP4(self.path)
        thumbnail_data = None
        if "covr" in mp4:
            thumbnail_data = bytes(mp4["covr"][0])
        return thumbnail_data

    async def get_thumbnail(self) -> bytes | None:
        return await tracer.Async.call_raise(self._get_thumbnail)

    @classmethod
    async def load(cls, path: Path) -> MP4 | None:
        return await tracer.Async.call_raise(cls._load, path)

    async def _as_mp3(self) -> MP3:
        """Extract the MP4 file to an MP3 file."""
        LOGGER.debug("MP3 audio extraction - %s", self.filename)
        mp3_path = self.path.with_suffix(".mp3")
        (
            ffmpeg.input(str(self.path))
            .output(str(mp3_path), format="mp3", acodec="libmp3lame", **{"qscale:a": 1}, loglevel="quiet")
            .run(overwrite_output=True)
        )
        LOGGER.debug("extraction completed - %s", self.filename)
        mp3 = MP3(title=self.title, author=self.author, path=mp3_path, duration=self.duration)
        thumbnail = await self.get_thumbnail()
        await mp3.save(thumbnail=thumbnail)
        LOGGER.debug("MP3 metadata saved - %s", mp3_path)
        return mp3

    async def as_mp3(self) -> MP3:
        return await tracer.Async.call_raise(self._as_mp3)
