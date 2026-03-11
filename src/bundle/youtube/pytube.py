from __future__ import annotations

import asyncio
from functools import partial
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlparse

from pytubefix import Playlist, YouTube
from pytubefix.exceptions import PytubeFixError

from bundle.core import logger, tracer

from . import POTO_TOKEN_PATH
from .browser import PotoTokenBrowser, PotoTokenEntity
from .track import YoutubeResolveOptions, YoutubeStreamOption, YoutubeTrackData

log = logger.get_logger(__name__)


def _playlist_id(url: str) -> str | None:
    """Return the playlist ID from any YouTube URL that contains one, or None."""
    query = parse_qs(urlparse(url).query)
    ids = query.get("list", [])
    return ids[0] if ids else None


def _has_video_id(url: str) -> bool:
    """Return True if the URL contains a ``v=`` parameter (single video)."""
    query = parse_qs(urlparse(url).query)
    return bool(query.get("v"))


CLIENT_PROFILES: tuple[dict[str, object], ...] = (
    {"client": "ANDROID_VR"},
    {"client": "ANDROID"},
    {"client": "IOS"},
    {"client": "WEB"},
)


@tracer.Async.decorator.call_raise
async def generate_token():
    async with PotoTokenBrowser.chromium(headless=False) as ptb:
        poto_entity = await ptb.extract_token()
        if poto_entity.name != "unknow":
            await poto_entity.dump_json(POTO_TOKEN_PATH)
            log.info("poto token generated at %s", POTO_TOKEN_PATH)
        else:
            log.info("error generating the poto token")


@tracer.Sync.decorator.call_raise
def load_poto_token():
    if not POTO_TOKEN_PATH.exists():
        tracer.Sync.call_raise(generate_token)
    if POTO_TOKEN_PATH.exists():
        poto_entity = tracer.Sync.call_raise(PotoTokenEntity.from_json, POTO_TOKEN_PATH)
        return {"po_token": poto_entity.potoken, "visitor_data": poto_entity.visitor_data}


async def _stream_filesize(stream) -> int:
    try:
        size = getattr(stream, "filesize", None) or getattr(stream, "filesize_approx", None)
        if asyncio.iscoroutine(size):
            size = await size
        return int(size or 0)
    except Exception:
        return 0


def _stream_url(stream) -> str:
    try:
        return getattr(stream, "url", "") or ""
    except Exception:
        return ""


async def _stream_option(stream, kind: str) -> YoutubeStreamOption:
    filesize = await _stream_filesize(stream)
    return YoutubeStreamOption(
        itag=int(stream.itag),
        kind=kind,
        url=_stream_url(stream),
        resolution=getattr(stream, "resolution", "") or "",
        abr=getattr(stream, "abr", "") or "",
        fps=int(getattr(stream, "fps", 0) or 0),
        mime_type=getattr(stream, "mime_type", "") or "",
        progressive=bool(getattr(stream, "progressive", False)),
        filesize=filesize,
    )


def _pick_stream_by_itag(yt: YouTube, itag: int | None):
    if not itag:
        return None
    return yt.streams.get_by_itag(int(itag))


async def _collect_streams(yt: YouTube) -> tuple[list[YoutubeStreamOption], list[YoutubeStreamOption]]:
    progressive_video_streams = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc()
    adaptive_video_streams = (
        yt.streams.filter(adaptive=True, only_video=True, file_extension="mp4").order_by("resolution").desc()
    )
    video_streams = [*progressive_video_streams, *adaptive_video_streams]
    audio_streams = yt.streams.filter(only_audio=True, mime_type="audio/mp4").order_by("abr").desc()
    if len(audio_streams) == 0:
        audio_streams = yt.streams.filter(only_audio=True).order_by("abr").desc()
    video_options = [await _stream_option(stream, "video") for stream in video_streams]
    audio_options = [await _stream_option(stream, "audio") for stream in audio_streams]
    return _dedupe_options(video_options), _dedupe_options(audio_options)


def _dedupe_options(options: list[YoutubeStreamOption]) -> list[YoutubeStreamOption]:
    by_itag: dict[int, YoutubeStreamOption] = {}
    ordered: list[int] = []
    for option in options:
        if option.itag not in by_itag:
            by_itag[option.itag] = option
            ordered.append(option.itag)
            continue
        existing = by_itag[option.itag]
        if option.filesize > existing.filesize:
            by_itag[option.itag] = option
    return [by_itag[itag] for itag in ordered]


async def fetch_url_youtube_info(
    url: str,
    *,
    options: YoutubeResolveOptions | None = None,
) -> YoutubeTrackData:
    try:
        # Preprocess the URL
        log.debug(f"Original URL: {url}")
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get("v")
        if not video_id:
            # Handle short URLs like youtu.be or other formats
            if "youtu.be" in parsed_url.netloc:
                video_id = parsed_url.path.strip("/")
                log.debug(f"Extracted video ID from youtu.be URL: {video_id}")
            else:
                log.error(f"Invalid YouTube URL: {url}")
                return YoutubeTrackData()
        else:
            video_id = video_id[0]
            log.debug(f"Extracted video ID: {video_id}")

        # Construct a standard YouTube URL
        standard_url = f"https://www.youtube.com/watch?v={video_id}"
        log.debug(f"Standardized URL: {standard_url}")

        yt = await resolve_with_clients(standard_url)
        if yt is None:
            return YoutubeTrackData()
        resolve_options = options or YoutubeResolveOptions()
        video_options, audio_options = await _collect_streams(yt)
        selected_video_stream = _pick_stream_by_itag(yt, resolve_options.select_video_itag)
        selected_audio_stream = _pick_stream_by_itag(yt, resolve_options.select_audio_itag)

        if resolve_options.best and not selected_video_stream and video_options:
            selected_video_stream = _pick_stream_by_itag(yt, video_options[0].itag)
        if resolve_options.best and not selected_audio_stream and audio_options:
            selected_audio_stream = _pick_stream_by_itag(yt, audio_options[0].itag)

        log.debug(f"Fetched YouTube data: title='{yt.title}', author='{yt.author}'")

        return YoutubeTrackData(
            audio_url=selected_audio_stream.url if selected_audio_stream else "",
            video_url=selected_video_stream.url if selected_video_stream else "",
            audio_mime_type=getattr(selected_audio_stream, "mime_type", "") or "",
            video_mime_type=getattr(selected_video_stream, "mime_type", "") or "",
            thumbnail_url=yt.thumbnail_url,
            title=yt.title,
            author=yt.author,
            duration=yt.length,
            audio_streams=audio_options,
            video_streams=video_options,
        )
    except PytubeFixError as e:
        log.error(f"Failed to fetch YouTube data for {url}: {e}")
        return YoutubeTrackData()


async def resolve_with_clients(url: str) -> YouTube | None:
    loop = asyncio.get_event_loop()
    for profile in CLIENT_PROFILES:
        client_name = profile["client"]
        kwargs = {"client": client_name}
        try:
            yt = await loop.run_in_executor(None, partial(YouTube, url, **kwargs))
            # Verify streams are actually accessible (not just metadata)
            _ = yt.streams
            log.debug("Resolved %s using client %s", url, client_name)
            return yt
        except Exception as exc:
            log.warning("Client %s failed for %s: %s", client_name, url, exc)
            continue
    log.error("All clients failed to resolve %s", url)
    return None


async def fetch_playlist_urls(url: str) -> AsyncGenerator[str, None]:
    list_id = _playlist_id(url)
    playlist_url = f"https://www.youtube.com/playlist?list={list_id}" if list_id else url
    playlist = await tracer.Async.call_raise(Playlist, playlist_url)
    for video_url in playlist.video_urls:
        yield video_url


@tracer.Async.decorator.call_raise
async def is_playlist(url: str) -> bool:
    return _playlist_id(url) is not None


@tracer.Async.decorator.call_raise
async def resolve_single_url(
    url: str,
    *,
    options: YoutubeResolveOptions | None = None,
) -> YoutubeTrackData:
    return await fetch_url_youtube_info(url, options=options)


async def resolve_playlist_url(
    url: str,
    *,
    options: YoutubeResolveOptions | None = None,
) -> AsyncGenerator[YoutubeTrackData, None]:
    async for playlist_url in fetch_playlist_urls(url):
        yield await fetch_url_youtube_info(playlist_url, options=options)


async def resolve(
    url: str,
    *,
    options: YoutubeResolveOptions | None = None,
) -> AsyncGenerator[YoutubeTrackData, None]:
    log.debug("Resolving: %s", url)
    if await is_playlist(url):
        yielded = False
        try:
            async for playlist_url in fetch_playlist_urls(url):
                yield await fetch_url_youtube_info(playlist_url, options=options)
                yielded = True
        except Exception:
            log.warning("Playlist resolution failed for %s, falling back to single video", url)
        # Fall back to single video if playlist yielded nothing (e.g. Radio/Mix)
        if not yielded and _has_video_id(url):
            log.info("Falling back to single-video resolve for %s", url)
            yield await fetch_url_youtube_info(url, options=options)
    else:
        yield await fetch_url_youtube_info(url, options=options)


async def probe(url: str) -> AsyncGenerator[YoutubeTrackData, None]:
    async for track in resolve(url, options=YoutubeResolveOptions(best=False)):
        yield track
