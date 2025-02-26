import asyncio
from typing import AsyncGenerator
from urllib.parse import parse_qs, urlparse

from pytubefix import Playlist, YouTube
from pytubefix.exceptions import PytubeFixError

from bundle.core import logger, tracer

from . import POTO_TOKEN_PATH
from .browser import PotoTokenBrowser, PotoTokenEntity
from .data import YoutubeTrackData

log = logger.get_logger(__name__)

PLAYLIST_INDICATOR = "playlist"


async def generate_token():
    async with PotoTokenBrowser.chromium(headless=False) as ptb:
        poto_entity = await ptb.extract_token()
        if poto_entity.name != "unknow":
            await poto_entity.dump_json(POTO_TOKEN_PATH)
            log.info("poto token generated at %s", POTO_TOKEN_PATH)
        else:
            log.info("error generating the poto token")


def load_poto_token():
    if not POTO_TOKEN_PATH.exists():
        tracer.Sync.call_raise(generate_token)
    if POTO_TOKEN_PATH.exists():
        poto_entity = tracer.Sync.call_raise(PotoTokenEntity.from_json(POTO_TOKEN_PATH))
        return {"po_token": poto_entity.potoken, "visitor_data": poto_entity.visitor_data}


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

        yt = await asyncio.get_event_loop().run_in_executor(
            None, lambda: YouTube(standard_url, use_po_token=True, po_token_verifier=load_poto_token)
        )
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


async def fetch_playlist_urls(url: str) -> AsyncGenerator[str, None]:
    try:
        playlist = await asyncio.to_thread(Playlist, url, use_po_token=True)
        for video_url in playlist.video_urls:
            yield video_url

    except PytubeFixError as e:
        log.error(f"Failed to fetch playlist data for {url}: {e}")


async def resolve(url: str) -> AsyncGenerator[YoutubeTrackData, None]:
    log.debug("Resolving: %s", url)
    if PLAYLIST_INDICATOR in url:
        async for playlist_url in fetch_playlist_urls(url):
            yield await fetch_url_youtube_info(playlist_url)
    else:
        yield await fetch_url_youtube_info(url)
