# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""YouTube resolution through yt-dlp.

Same contract as ``bundle.youtube.pytube.resolve``: an async stream of
``YoutubeTrackData``, one per video, playlists expanded in order.

yt-dlp is used because it follows YouTube's client and token changes; stream
URLs resolved by pytubefix 11.2.1 are refused (HTTP 403) on most whole-file
reads, which is how ffmpeg and the downloader fetch them.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError

from bundle.core import logger

from .track import YoutubeResolveOptions, YoutubeStreamOption, YoutubeTrackData

log = logger.get_logger(__name__)

# Only formats a plain HTTP client can read end to end (no HLS manifests or storyboards).
STREAMABLE_PROTOCOLS = {"https", "http"}

BASE_OPTIONS: dict[str, Any] = {"quiet": True, "no_warnings": True, "skip_download": True}


def _extract(url: str, **options: Any) -> dict[str, Any]:
    """Blocking yt-dlp metadata extraction; run it in a worker thread."""
    with yt_dlp.YoutubeDL(BASE_OPTIONS | options) as ydl:
        return ydl.extract_info(url, download=False)


def _itag(format_id: str) -> int | None:
    """YouTube format ids are itags, sometimes suffixed (``251-drc``)."""
    head = format_id.split("-", 1)[0]
    return int(head) if head.isdigit() else None


def _stream_option(fmt: dict[str, Any], kind: str) -> YoutubeStreamOption:
    return YoutubeStreamOption(
        itag=_itag(fmt["format_id"]),
        kind=kind,
        url=fmt["url"],
        resolution=f"{fmt['height']}p" if fmt.get("height") else "",
        abr=f"{round(fmt['abr'])}kbps" if fmt.get("abr") else "",
        fps=int(fmt.get("fps") or 0),
        mime_type=f"{kind}/{fmt.get('ext', '')}",
        progressive=fmt.get("vcodec") != "none" and fmt.get("acodec") != "none",
        filesize=int(fmt.get("filesize") or fmt.get("filesize_approx") or 0),
    )


def _stream_options(info: dict[str, Any]) -> tuple[list[YoutubeStreamOption], list[YoutubeStreamOption]]:
    """Streamable video and audio options, best first."""
    formats = [f for f in info.get("formats", []) if f.get("protocol") in STREAMABLE_PROTOCOLS and _itag(f["format_id"])]
    audio = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
    video = [f for f in formats if f.get("vcodec") not in (None, "none")]
    audio.sort(key=lambda f: f.get("abr") or 0, reverse=True)
    video.sort(key=lambda f: (f.get("height") or 0, f.get("fps") or 0), reverse=True)
    return [_stream_option(f, "video") for f in video], [_stream_option(f, "audio") for f in audio]


def _select(options: list[YoutubeStreamOption], itag: int | None, best: bool) -> YoutubeStreamOption | None:
    if itag is not None:
        return next((option for option in options if option.itag == itag), None)
    return options[0] if best and options else None


def track_from_info(info: dict[str, Any], options: YoutubeResolveOptions | None = None) -> YoutubeTrackData:
    """Map one yt-dlp video ``info`` dict to the bundle track model."""
    options = options or YoutubeResolveOptions()
    video_options, audio_options = _stream_options(info)
    video = _select(video_options, options.select_video_itag, options.best)
    audio = _select(audio_options, options.select_audio_itag, options.best)
    return YoutubeTrackData(
        title=info.get("title") or "",
        author=info.get("uploader") or info.get("channel") or "",
        duration=int(info.get("duration") or 0),
        thumbnail_url=info.get("thumbnail") or "",
        audio_url=audio.url if audio else "",
        video_url=video.url if video else "",
        audio_mime_type=audio.mime_type if audio else "",
        video_mime_type=video.mime_type if video else "",
        audio_streams=audio_options,
        video_streams=video_options,
    )


async def resolve(
    url: str,
    *,
    options: YoutubeResolveOptions | None = None,
    limit: int | None = None,
) -> AsyncGenerator[YoutubeTrackData, None]:
    """Yield resolved tracks for a video or playlist URL; ``limit`` caps playlist entries."""
    log.debug("Resolving with yt-dlp: %s", url)
    listing = await asyncio.to_thread(_extract, url, extract_flat="in_playlist", playlistend=limit)
    if listing.get("_type") != "playlist":
        # Flat mode only skips playlist entries: a single video comes back fully extracted.
        yield track_from_info(listing, options)
        return
    for entry in listing.get("entries") or []:
        entry_url = entry.get("url") or entry.get("webpage_url")
        if not entry_url:
            continue
        try:
            yield track_from_info(await asyncio.to_thread(_extract, entry_url, noplaylist=True), options)
        except DownloadError as error:
            log.warning("Skipping unavailable playlist entry %s: %s", entry_url, error)
