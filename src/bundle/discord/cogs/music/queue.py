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

"""Track queue -- pure data operations, no Discord API."""

from __future__ import annotations

import random

from bundle.youtube.track import YoutubeTrackData


class TrackQueue:
    """Ordered track list with a cursor."""

    def __init__(self) -> None:
        self._tracks: list[YoutubeTrackData] = []
        self._index: int = -1
        self.resolving: bool = False
        self.waiting: bool = False  # cursor past end, waiting for more tracks

    # ---- properties ----

    @property
    def tracks(self) -> list[YoutubeTrackData]:
        return self._tracks

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int) -> None:
        self._index = value

    @property
    def current(self) -> YoutubeTrackData | None:
        if 0 <= self._index < len(self._tracks):
            return self._tracks[self._index]
        return None

    @property
    def has_next(self) -> bool:
        return self._index + 1 < len(self._tracks)

    @property
    def has_prev(self) -> bool:
        return self._index > 0

    def __len__(self) -> int:
        return len(self._tracks)

    def __bool__(self) -> bool:
        return bool(self._tracks)

    # ---- mutations ----

    def enqueue(self, track: YoutubeTrackData) -> int:
        """Append a track; return its index."""
        self._tracks.append(track)
        return len(self._tracks) - 1

    def advance(self, delta: int = 1) -> bool:
        """Move cursor by *delta*.  Return True if the new position is valid."""
        target = self._index + delta
        if 0 <= target < len(self._tracks):
            self._index = target
            return True
        return False

    def shuffle(self) -> None:
        """Shuffle remaining tracks after the current cursor position."""
        start = self._index + 1
        if start >= len(self._tracks):
            return
        tail = self._tracks[start:]
        random.shuffle(tail)
        self._tracks[start:] = tail

    # ---- display ----

    def pos_str(self) -> str:
        suffix = "+" if self.resolving else ""
        return f"{self._index + 1} / {len(self._tracks)}{suffix}"
