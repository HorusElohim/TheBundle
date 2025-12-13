from __future__ import annotations

import asyncio
from functools import partial
from typing import AsyncGenerator
from urllib.parse import parse_qs, urlparse

from pytubefix import Playlist, YouTube
from pytubefix.exceptions import PytubeFixError

from bundle.core import logger, tracer

from . import POTO_TOKEN_PATH
from .browser import PotoTokenBrowser, PotoTokenEntity
from .track import YoutubeTrackData

log = logger.get_logger(__name__)

PLAYLIST_INDICATOR = "playlist"
CLIENT_PROFILES: tuple[dict[str, object], ...] = (
    {"client": "ANDROID"},
    {"client": "ANDROID_CREATOR"},
    {"client": "IOS"},
    {"client": "WEB", "use_po_token": True},
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


@tracer.Async.decorator.call_raise
async def fetch_url_youtube_info(url: str) -> YoutubeTrackData:
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
        audio_stream = yt.streams.get_audio_only()
        video_stream = yt.streams.get_highest_resolution()

        log.debug(f"Fetched YouTube data: title='{yt.title}', author='{yt.author}'")

        return YoutubeTrackData(
            audio_url=audio_stream.url if audio_stream else "",
            video_url=video_stream.url if video_stream else "",
            thumbnail_url=yt.thumbnail_url,
            title=yt.title,
            author=yt.author,
            duration=yt.length,
        )
    except PytubeFixError as e:
        log.error(f"Failed to fetch YouTube data for {url}: {e}")
        return YoutubeTrackData()


async def resolve_with_clients(url: str) -> YouTube | None:
    loop = asyncio.get_event_loop()
    for profile in CLIENT_PROFILES:
        client_name = profile["client"]
        kwargs = {"client": client_name}
        if profile.get("use_po_token"):
            kwargs.update({"use_po_token": True, "po_token_verifier": load_poto_token})
        try:
            yt = await loop.run_in_executor(None, partial(YouTube, url, **kwargs))
            log.debug("Resolved %s using client %s", url, client_name)
            return yt
        except PytubeFixError as exc:
            log.warning("Client %s failed to resolve %s: %s", client_name, url, exc)
            continue
    log.error("All clients failed to resolve %s", url)
    return None


async def fetch_playlist_urls(url: str) -> AsyncGenerator[str, None]:
    playlist = await tracer.Async.call_raise(Playlist, url, use_po_token=True)
    for video_url in playlist.video_urls:
        yield video_url


@tracer.Async.decorator.call_raise
async def is_playlist(url: str):
    return PLAYLIST_INDICATOR in url


@tracer.Async.decorator.call_raise
async def resolve_single_url(url: str) -> YoutubeTrackData:
    return await fetch_url_youtube_info(url)


async def resolve_playlist_url(url: str) -> AsyncGenerator[YoutubeTrackData, None]:
    async for playlist_url in fetch_playlist_urls(url):
        yield await fetch_url_youtube_info(playlist_url)


async def resolve(url: str) -> AsyncGenerator[YoutubeTrackData, None]:
    log.debug("Resolving: %s", url)
    if await is_playlist(url):
        async for playlist_url in fetch_playlist_urls(url):
            yield await fetch_url_youtube_info(playlist_url)
    else:
        yield await fetch_url_youtube_info(url)
