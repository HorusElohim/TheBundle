# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import hashlib
import re
from pathlib import Path
from typing import Literal

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
    def post_init(self):
        self.author = sanitize_string(self.author)
        self.title = sanitize_string(self.title)
        self.filename = f"{self.author}-{self.title}"
        self.identifier = get_identifier(self.filename)
        return self


class YoutubeTrackData(TrackData):
    audio_url: str = data.Field(default_factory=str)
    video_url: str = data.Field(default_factory=str)
    thumbnail_url: str = data.Field(default_factory=str)
    audio_mime_type: str = data.Field(default_factory=str)
    video_mime_type: str = data.Field(default_factory=str)
    audio_streams: list["YoutubeStreamOption"] = data.Field(default_factory=list)
    video_streams: list["YoutubeStreamOption"] = data.Field(default_factory=list)

    def is_resolved(self) -> bool:
        """Return True when the resolver filled the stream URLs."""
        return bool(
            self.video_url.strip()
            or self.audio_url.strip()
            or self.video_streams
            or self.audio_streams
        )


class YoutubeStreamOption(data.Data):
    itag: int
    kind: Literal["audio", "video"]
    url: str = data.Field(default_factory=str)
    resolution: str = data.Field(default_factory=str)
    abr: str = data.Field(default_factory=str)
    fps: int = 0
    mime_type: str = data.Field(default_factory=str)
    progressive: bool = False
    filesize: int = 0


class YoutubeResolveOptions(data.Data):
    select_video_itag: int | None = None
    select_audio_itag: int | None = None
    best: bool = True


class MP3TrackData(TrackData):
    path: Path


class MP4TrackData(TrackData):
    path: Path
