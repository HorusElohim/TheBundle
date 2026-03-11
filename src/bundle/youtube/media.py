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

import asyncio
from pathlib import Path
from typing import Type

import ffmpeg
from mutagen.id3 import APIC, ID3, TIT2, TPE1, error
from mutagen.mp3 import MP3 as MutagenMP3
from mutagen.mp4 import MP4 as MutagenMP4
from mutagen.mp4 import MP4Cover

from ..core import downloader, logger, tracer
from .track import MP3TrackData, MP4TrackData, TrackData, YoutubeTrackData

log = logger.get_logger(__name__)


def is_mp4_container(path: Path) -> bool:
    """
    Quick MP4 sanity check: MP4 files contain an `ftyp` box near the beginning.
    """
    try:
        with path.open("rb") as fp:
            head = fp.read(64)
    except OSError:
        return False
    if len(head) < 12:
        return False
    return b"ftyp" in head[:32]


@tracer.Async.decorator.call_raise
async def download_mp4(youtube_track: YoutubeTrackData, destination_folder: Path) -> MP4:
    """
    Download an MP4 file from video_url to destination.
    This wraps your existing DownloaderTQDM logic.
    """

    target_path = destination_folder / f"{youtube_track.filename}.mp4"
    audio_downloader = downloader.DownloaderTQDM(url=youtube_track.video_url, destination=target_path)
    thumbnail_downloader = downloader.Downloader(url=youtube_track.thumbnail_url)

    await asyncio.gather(audio_downloader.download(), thumbnail_downloader.download())

    mp4 = MP4.from_track(path=target_path, track=youtube_track)
    await mp4.save(thumbnail_downloader.buffer)

    return mp4


@tracer.Async.decorator.call_raise
async def extract_mp3(mp4: MP4) -> MP3:
    """Extract the MP4 file to an MP3 file."""
    assert isinstance(mp4, MP4), f"Only accept MP4 class not '{type(mp4)}'"

    log.debug("MP3 audio extraction - %s", mp4.filename)
    mp3_path = mp4.path.with_suffix(".mp3")
    (
        ffmpeg.input(str(mp4.path))
        .output(str(mp3_path), format="mp3", acodec="libmp3lame", **{"qscale:a": 1}, loglevel="quiet")
        .run(overwrite_output=True)
    )
    log.debug("extraction completed - %s", mp4.filename)
    mp3 = MP3(title=mp4.title, author=mp4.author, path=mp3_path, duration=mp4.duration)
    await mp3.save(thumbnail=await mp4.get_thumbnail())
    log.debug("mp3 generated -> %s", mp3_path)
    return mp3


def _extension_from_mime(mime_type: str, default: str) -> str:
    mime = (mime_type or "").lower()
    if "audio/mp4" in mime or "video/mp4" in mime:
        return ".m4a" if "audio" in mime else ".mp4"
    if "webm" in mime:
        return ".webm"
    return default


def audio_target_path(youtube_track: YoutubeTrackData, destination_folder: Path) -> Path:
    extension = _extension_from_mime(youtube_track.audio_mime_type, ".m4a")
    return destination_folder / f"{youtube_track.filename}{extension}"


@tracer.Async.decorator.call_raise
async def download_audio(youtube_track: YoutubeTrackData, destination_folder: Path) -> Path:
    if not youtube_track.audio_url:
        raise ValueError("Missing audio URL for download")
    target_path = audio_target_path(youtube_track, destination_folder)
    audio_downloader = downloader.DownloaderTQDM(url=youtube_track.audio_url, destination=target_path)
    await audio_downloader.download()
    return target_path


@tracer.Async.decorator.call_raise
async def extract_mp3_from_path(source_path: Path, track: TrackData, thumbnail: None | bytes = None) -> MP3:
    mp3_path = source_path.with_suffix(".mp3")
    (
        ffmpeg.input(str(source_path))
        .output(str(mp3_path), format="mp3", acodec="libmp3lame", **{"qscale:a": 1}, loglevel="quiet")
        .run(overwrite_output=True)
    )
    mp3 = MP3.from_track(path=mp3_path, track=track)
    await mp3.save(thumbnail=thumbnail)
    return mp3


class MP3(MP3TrackData):
    @classmethod
    def from_track(cls: type[MP3], path, track: TrackData):
        return cls(path=path, author=track.author, title=track.title, duration=track.duration)

    @tracer.Async.decorator.call_raise
    async def save(self, thumbnail: None | bytes = None) -> None:
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

    @tracer.Async.decorator.call_raise
    async def get_thumbnail(self) -> bytes:
        mp3 = MutagenMP3(self.path, ID3=ID3)
        thumbnail_data = b""
        if mp3.tags and "APIC:Cover" in mp3.tags:
            thumbnail_data = mp3.tags["APIC:Cover"].data
        return thumbnail_data

    @classmethod
    @tracer.Async.decorator.call_raise
    async def load(cls, path: Path) -> MP3 | None:
        mp3 = MutagenMP3(path, ID3=ID3)
        raw_title = mp3.get("TIT2", [None])
        if raw_title:
            title = raw_title[0]
        raw_author = mp3.get("TPE1", [None])
        if raw_author:
            author = raw_author[0]
        duration = int(mp3.info.length)
        return MP3(path=path, title=title, author=author, duration=duration)


class MP4(MP4TrackData):
    @classmethod
    def from_track(cls: type[MP4], path, track: TrackData):
        return cls(path=path, author=track.author, title=track.title, duration=track.duration)

    @tracer.Async.decorator.call_raise
    async def save(self, thumbnail: None | bytes = None) -> None:
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

    @tracer.Async.decorator.call_raise
    async def get_thumbnail(self) -> bytes | None:
        mp4 = MutagenMP4(self.path)
        thumbnail_data = None
        if "covr" in mp4:
            thumbnail_data = bytes(mp4["covr"][0])
        return thumbnail_data

    @classmethod
    @tracer.Async.decorator.call_raise
    async def load(cls, path: Path) -> MP4 | None:
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

    @classmethod
    @tracer.Async.decorator.call_raise
    async def download(cls, youtube_track: YoutubeTrackData, destination_folder: Path) -> MP4:
        return await download_mp4(youtube_track, destination_folder)

    @tracer.Async.decorator.call_raise
    async def extract_mp3(self) -> MP3:
        return await extract_mp3(self)
