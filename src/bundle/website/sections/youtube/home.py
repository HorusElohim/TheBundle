import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from bundle.core.downloader import Downloader
from bundle.youtube.media import MP4
from bundle.youtube.pytube import resolve
from bundle.youtube.track import YoutubeTrackData

from ...common.downloader import DownloaderWebSocket
from ...common.sections import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "youtube"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

MUSIC_PATH = Path(__file__).parent / "static"


router = APIRouter()
templates = create_templates(TEMPLATE_PATH)


class TrackMetadata(YoutubeTrackData):
    type: str = "metadata"


@router.get("/youtube", response_class=HTMLResponse)
async def youtube(request: Request):
    return templates.TemplateResponse("youtube.html", base_context(request))


@router.websocket("/ws/youtube/download_track")
async def download_track(websocket: WebSocket):
    await websocket.accept()
    LOGGER.debug("callback called from websocket url: %s", websocket.url)
    while True:
        try:
            data = await websocket.receive_json()
        except WebSocketDisconnect:
            LOGGER.debug("YouTube websocket disconnected: %s", websocket.client)
            break

        LOGGER.debug("received: %s", data)
        youtube_url = data.get("youtube_url", "")
        requested_format = data.get("format", "mp4").lower()
        if requested_format not in {"mp3", "mp4"}:
            requested_format = "mp4"

        await websocket.send_text(json.dumps({"type": "info", "info_message": "Resolving YouTube track"}))
        resolved_any = False
        async for youtube_track in resolve(youtube_url):
            if youtube_track is None or not youtube_track.is_resolved():
                await websocket.send_text(
                    json.dumps({"type": "info", "info_message": "Skipping unresolved entry from playlist"})
                )
                continue

            resolved_any = True
            youtube_track_json = await TrackMetadata(**await youtube_track.as_dict()).as_json()
            await websocket.send_text(youtube_track_json)

            destination = MUSIC_PATH / f"{youtube_track.filename}.mp4"
            audio_downloader = DownloaderWebSocket(url=youtube_track.video_url, destination=destination)
            await audio_downloader.set_websocket(websocket=websocket)
            thumbnail_downloader = Downloader(url=youtube_track.thumbnail_url)
            await asyncio.gather(audio_downloader.download(), thumbnail_downloader.download())

            await websocket.send_text(
                json.dumps({"type": "info", "info_message": f"Embedding metadata for {youtube_track.filename}"})
            )
            mp4 = MP4.from_track(path=destination, track=youtube_track)
            await mp4.save(thumbnail_downloader.buffer)

            served_path = mp4.path
            if requested_format == "mp3":
                await websocket.send_text(json.dumps({"type": "info", "info_message": "Extracting MP3 audio"}))
                mp3 = await mp4.extract_mp3()
                served_path = mp3.path

            file_url = f"/youtube/{served_path.name}"
            await websocket.send_text(json.dumps({"type": "info", "info_message": "Download ready"}))
            await websocket.send_text(
                json.dumps({"type": "file_ready", "url": file_url, "filename": served_path.name, "format": requested_format})
            )

        if not resolved_any:
            await websocket.send_text(json.dumps({"type": "info", "info_message": "Unable to resolve any playable entries"}))

        await websocket.send_text(json.dumps({"type": "completed"}))
