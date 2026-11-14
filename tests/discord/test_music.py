# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""Music playback: jitter buffer and guild player behavior.

Only the edges are faked (the ffmpeg-backed source and the Discord voice
client); BufferedOpusAudio and GuildPlayer run unmodified.
"""

from __future__ import annotations

import threading

import discord
import pytest
from discord.opus import OPUS_SILENCE

from bundle.discord.cogs.music import MAX_CONSECUTIVE_FAILURES, MusicCog
from bundle.discord.cogs.music import player as player_module
from bundle.discord.cogs.music.player import GuildPlayer, TrackProducedNoAudio
from bundle.discord.cogs.music.source import BufferedOpusAudio
from bundle.discord.embeds import EmbedFactory
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


@pytest.mark.asyncio
async def test_player_builds_the_source_off_the_event_loop(built_sources) -> None:
    track = YoutubeTrackData(title="t", audio_url="https://audio")

    await GuildPlayer(ignore_track_end).play(VoiceClient(), track, GUILD_ID)

    _, on_loop_thread = built_sources[0]
    assert not on_loop_thread, "make_source blocks up to 10 s pre-filling; it must not freeze the bot"


async def play_to_the_end(monkeypatch: pytest.MonkeyPatch, frames: list[bytes]) -> tuple[GuildPlayer, list[Exception | None]]:
    """Play one track whose ffmpeg output is `frames`, then fire Discord's after-callback."""
    ended_with: list[Exception | None] = []

    async def on_track_end(guild_id: int, error: Exception | None) -> None:
        ended_with.append(error)

    player = GuildPlayer(on_track_end)
    voice = VoiceClient()
    monkeypatch.setattr(player_module, "make_source", lambda url: BufferedOpusAudio(ScriptedSource(frames)))
    await player.play(voice, YoutubeTrackData(title="t", audio_url="https://audio"), GUILD_ID)
    drain(voice.source)
    await player._after_track(GUILD_ID, None)
    return player, ended_with


@pytest.mark.asyncio
async def test_a_track_that_produced_no_audio_ends_as_a_failure(monkeypatch) -> None:
    player, ended_with = await play_to_the_end(monkeypatch, [])

    assert isinstance(ended_with[0], TrackProducedNoAudio)
    assert player.consecutive_failures == 1


@pytest.mark.asyncio
async def test_a_track_that_played_resets_the_failure_count(monkeypatch) -> None:
    player, ended_with = await play_to_the_end(monkeypatch, [FRAME])

    assert ended_with == [None]
    assert player.consecutive_failures == 0


class TextChannel:
    def __init__(self) -> None:
        self.sent: list[discord.Embed] = []

    async def send(self, *, embed: discord.Embed, **_) -> None:
        self.sent.append(embed)


class ConnectedVoice(VoiceClient):
    def __init__(self) -> None:
        super().__init__()
        self.disconnected = False

    def is_playing(self) -> bool:
        return False

    def is_paused(self) -> bool:
        return False

    def is_connected(self) -> bool:
        return not self.disconnected

    async def disconnect(self) -> None:
        self.disconnected = True


class Guild:
    def __init__(self) -> None:
        self.id = GUILD_ID
        self.voice_client = ConnectedVoice()


class Bot:
    def __init__(self, guild: Guild) -> None:
        self.guild = guild
        self.embeds = EmbedFactory("Oltre")

    def get_guild(self, guild_id: int) -> Guild | None:
        return self.guild if guild_id == self.guild.id else None


@pytest.mark.asyncio
async def test_repeated_unplayable_tracks_stop_playback_instead_of_draining_the_queue(monkeypatch) -> None:
    monkeypatch.setattr(player_module, "make_source", lambda url: BufferedOpusAudio(ScriptedSource([])))
    guild, channel = Guild(), TextChannel()
    cog = MusicCog(Bot(guild))
    session = cog._ensure_session(GUILD_ID, channel)
    for n in range(50):
        session.queue.enqueue(YoutubeTrackData(title=f"mix track {n}", audio_url=f"https://audio/{n}"))
    session.queue.advance()
    session.player.consecutive_failures = MAX_CONSECUTIVE_FAILURES

    await cog._on_track_end(GUILD_ID, TrackProducedNoAudio("no audio"))

    assert cog._get_session(GUILD_ID) is None, "the session is stopped"
    assert guild.voice_client.disconnected
    assert "could not be played" in channel.sent[-1].description
