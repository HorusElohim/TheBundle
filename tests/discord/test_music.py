# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""Music playback: jitter buffer and guild player behavior.

Only the edges are faked (the ffmpeg-backed source and the Discord voice
client); BufferedOpusAudio and GuildPlayer run unmodified.
"""

from __future__ import annotations

import threading

import pytest
from discord.opus import OPUS_SILENCE

from bundle.discord.cogs.music import player as player_module
from bundle.discord.cogs.music.player import GuildPlayer
from bundle.discord.cogs.music.source import BufferedOpusAudio
from bundle.youtube.track import YoutubeTrackData

FRAME = b"opus-frame"
GUILD_ID = 42


class ScriptedSource:
    """Stands in for FFmpegOpusAudio: yields scripted frames, may stall mid-stream."""

    def __init__(self, frames: list[bytes], stall: threading.Event | None = None) -> None:
        self.frames = list(frames)
        self.stall = stall
        self.cleaned_up = False

    def read(self) -> bytes:
        if self.frames:
            return self.frames.pop(0)
        if self.stall is not None:
            self.stall.wait(timeout=5)
        return b""

    def cleanup(self) -> None:
        self.cleaned_up = True


def drain(audio: BufferedOpusAudio, limit: int = 50) -> list[bytes]:
    frames = []
    for _ in range(limit):
        frame = audio.read()
        frames.append(frame)
        if not frame:
            break
    return frames


def test_buffer_underrun_plays_silence_instead_of_ending_the_track() -> None:
    network_recovered = threading.Event()
    audio = BufferedOpusAudio(ScriptedSource([FRAME], stall=network_recovered))

    assert audio.read() == FRAME
    assert audio.read() == OPUS_SILENCE, "a stalled stream must not end the track"

    network_recovered.set()
    assert drain(audio)[-1] == b"", "the track ends once ffmpeg really finishes"


class VoiceClient:
    """Records what the player hands to Discord."""

    def __init__(self) -> None:
        self.source = None
        self.after = None

    def play(self, source, *, after) -> None:
        self.source = source
        self.after = after


@pytest.fixture
def built_sources(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, bool]]:
    """Replace ffmpeg source creation; record (url, ran_on_event_loop_thread)."""
    built: list[tuple[str, bool]] = []
    loop_thread = threading.get_ident()

    def make_source(stream_url: str) -> BufferedOpusAudio:
        built.append((stream_url, threading.get_ident() == loop_thread))
        return BufferedOpusAudio(ScriptedSource([FRAME]))

    monkeypatch.setattr(player_module, "make_source", make_source)
    return built


async def ignore_track_end(guild_id: int, error: Exception | None) -> None:
    pass


@pytest.mark.asyncio
async def test_player_streams_the_audio_only_track(built_sources) -> None:
    track = YoutubeTrackData(title="t", audio_url="https://audio", video_url="https://video-4k")

    assert await GuildPlayer(ignore_track_end).play(VoiceClient(), track, GUILD_ID)

    assert built_sources[0][0] == "https://audio"
