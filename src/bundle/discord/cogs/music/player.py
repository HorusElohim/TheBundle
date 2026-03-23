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

"""Guild voice playback -- timing, pause/resume."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from typing import Any

import discord

from bundle.core import logger
from bundle.youtube.track import YoutubeTrackData

from .source import make_source

log = logger.get_logger(__name__)


class GuildPlayer:
    """Owns voice playback and timing for a single guild."""

    def __init__(
        self,
        on_track_end: Callable[[int, Exception | None], Coroutine[Any, Any, None]],
    ) -> None:
        self._on_track_end = on_track_end

        # Timing
        self.play_started_at: float = 0.0
        self.pause_offset: float = 0.0
        self.paused_at: float | None = None

        # Skip coordination
        self._skip_pending: bool = False

    # ---- timing ----

    def elapsed_secs(self) -> int:
        if self.play_started_at == 0:
            return 0
        if self.paused_at is not None:
            return int(self.paused_at - self.play_started_at - self.pause_offset)
        return int(time.monotonic() - self.play_started_at - self.pause_offset)

    def _reset_timing(self) -> None:
        self.play_started_at = time.monotonic()
        self.pause_offset = 0.0
        self.paused_at = None

    # ---- playback ----

    def play(self, vc: discord.VoiceClient, track: YoutubeTrackData, guild_id: int) -> bool:
        """Start FFmpeg playback.  Returns False if no stream URL available."""
        stream_url = track.video_url or track.audio_url
        if not stream_url:
            log.warning("No stream URL for track '%s'", track.title)
            return False

        self._reset_timing()

        loop = asyncio.get_running_loop()
        source = make_source(stream_url)
        vc.play(
            source,
            after=lambda err: asyncio.run_coroutine_threadsafe(self._after_track(guild_id, err), loop),
        )
        return True

    def pause(self, vc: discord.VoiceClient) -> bool:
        """Pause playback.  Returns True if state changed."""
        if vc.is_playing():
            vc.pause()
            self.paused_at = time.monotonic()
            return True
        return False

    def resume(self, vc: discord.VoiceClient) -> bool:
        """Resume playback.  Returns True if state changed."""
        if vc.is_paused():
            vc.resume()
            self.pause_offset += time.monotonic() - (self.paused_at or time.monotonic())
            self.paused_at = None
            return True
        return False

    def stop(self, vc: discord.VoiceClient) -> None:
        """Stop current source, suppress the after callback."""
        self._skip_pending = True
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        else:
            self._skip_pending = False

    # ---- internal ----

    async def _after_track(self, guild_id: int, error: Exception | None) -> None:
        if error:
            log.error("Playback error in guild %s: %s", guild_id, error)
        if self._skip_pending:
            self._skip_pending = False
            return
        await self._on_track_end(guild_id, error)
