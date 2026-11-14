# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""Music playback: jitter buffer and guild player behavior.

Only the edges are faked (the ffmpeg-backed source and the Discord voice
client); BufferedOpusAudio and GuildPlayer run unmodified.
"""

from __future__ import annotations

import threading

from discord.opus import OPUS_SILENCE

from bundle.discord.cogs.music.source import BufferedOpusAudio

FRAME = b"opus-frame"


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
