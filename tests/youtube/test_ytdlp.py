# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""yt-dlp resolver: info-dict mapping and playlist expansion (network faked at _extract)."""

from __future__ import annotations

import pytest

from bundle.youtube import ytdlp
from bundle.youtube.track import YoutubeResolveOptions


def fmt(format_id: str, *, protocol: str = "https", vcodec: str = "none", acodec: str = "none", **extra) -> dict:
    return {
        "format_id": format_id,
        "protocol": protocol,
        "vcodec": vcodec,
        "acodec": acodec,
        "url": f"https://gv/{format_id}",
        **extra,
    }


# Shape taken from a real yt-dlp 2026.10.26 extraction of a 4K live set.
VIDEO_INFO = {
    "id": "3o0T4z6oT4Y",
    "title": "Live at Tomorrowland",
    "uploader": "Dimitri Vegas & Like Mike",
    "duration": 4574,
    "thumbnail": "https://i.ytimg.com/maxres.jpg",
    "formats": [
        fmt("sb0", protocol="mhtml"),
        fmt("139", acodec="mp4a.40.5", ext="m4a", abr=48.7),
        fmt("140", acodec="mp4a.40.2", ext="m4a", abr=129.4, filesize=74030920),
        fmt("251-drc", acodec="opus", ext="webm", abr=125.2),
        fmt("140-hls", protocol="m3u8_native", acodec="mp4a.40.2", ext="mp4", abr=999),
        fmt("137", vcodec="avc1", ext="mp4", height=1080, fps=25),
        fmt("401", vcodec="av01", ext="mp4", height=2160, fps=25, filesize_approx=5650755950),
    ],
}


def test_best_streams_are_the_highest_quality_streamable_formats() -> None:
    track = ytdlp.track_from_info(VIDEO_INFO)

    assert track.audio_url == "https://gv/140", "HLS and storyboards are not streamable over plain HTTP"
    assert track.video_url == "https://gv/401"
    assert (track.audio_mime_type, track.video_mime_type) == ("audio/m4a", "video/mp4")
    assert (track.title, track.author, track.duration) == ("Live at Tomorrowland", "Dimitri Vegas Like Mike", 4574)


def test_stream_options_expose_itags_sizes_and_quality_labels() -> None:
    track = ytdlp.track_from_info(VIDEO_INFO)

    assert [option.itag for option in track.audio_streams] == [140, 251, 139]
    assert [option.resolution for option in track.video_streams] == ["2160p", "1080p"]
    assert track.audio_streams[0].abr == "129kbps"
    assert track.video_streams[0].filesize == 5650755950


def test_explicit_itags_select_those_streams() -> None:
    track = ytdlp.track_from_info(VIDEO_INFO, YoutubeResolveOptions(select_audio_itag=251, select_video_itag=137))

    assert (track.audio_url, track.video_url) == ("https://gv/251-drc", "https://gv/137")


def test_probe_mode_lists_streams_without_selecting_any() -> None:
    track = ytdlp.track_from_info(VIDEO_INFO, YoutubeResolveOptions(best=False))

    assert (track.audio_url, track.video_url) == ("", "")
    assert track.is_resolved(), "stream options alone make a probed track resolved"


@pytest.mark.asyncio
async def test_a_single_video_is_resolved_with_one_extraction(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    def extract(url: str, **options) -> dict:
        calls.append((url, options))
        return VIDEO_INFO

    monkeypatch.setattr(ytdlp, "_extract", extract)

    tracks = [track async for track in ytdlp.resolve("https://youtu.be/3o0T4z6oT4Y")]

    assert [track.title for track in tracks] == ["Live at Tomorrowland"]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_a_playlist_yields_each_entry_in_order_and_skips_unavailable_ones(monkeypatch) -> None:
    listing = {
        "_type": "playlist",
        "entries": [{"url": "https://yt/a"}, {"url": "https://yt/private"}, {"url": "https://yt/b"}],
    }

    def extract(url: str, **options) -> dict:
        if url == "https://yt/mix":
            assert options["playlistend"] == 2
            return listing
        if url == "https://yt/private":
            raise ytdlp.DownloadError("Private video")
        return VIDEO_INFO | {"title": url.rsplit("/", 1)[-1]}

    monkeypatch.setattr(ytdlp, "_extract", extract)

    tracks = [track async for track in ytdlp.resolve("https://yt/mix", limit=2)]

    assert [track.title for track in tracks] == ["a", "b"]
