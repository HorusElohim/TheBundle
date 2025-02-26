import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bundle.core.downloader import Downloader
from bundle.youtube.track import YoutubeTrackData
from bundle.youtube.media import MP4
from bundle.youtube.pytube import resolve

from ...common.downloader import DownloaderWebSocket
from ...common.sections import get_logger, get_static_path, get_template_path

NAME = "youtube"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

MUSIC_PATH = Path(__file__).parent / "static"


router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATE_PATH)


class TrackMetadata(YoutubeTrackData):
    type: str = "metadata"


@router.get("/youtube", response_class=HTMLResponse)
async def youtube(request: Request):
    return templates.TemplateResponse("youtube.html", {"request": request})


@router.websocket("/ws/youtube/download_track")
async def download_track(websocket: WebSocket):
    await websocket.accept()
    LOGGER.debug("callback called from websocket url: %s", websocket.url)
    while True:
        data = await websocket.receive_json()
        LOGGER.debug("received: %s", data)
        youtube_url = data["youtube_url"]
        format = str(data["format"])

        await websocket.send_text(json.dumps({"type": "info", "info_message": "Resolving YouTube track"}))
        async for youtube_track in resolve(youtube_url):
            LOGGER.debug("YoutubeTrack: %s", youtube_track.filename)
            if youtube_track is None:
                break
            youtube_track_json = await TrackMetadata(**await youtube_track.as_dict()).as_json()
            await websocket.send_text(youtube_track_json)
            destination = MUSIC_PATH / f"{youtube_track.filename}.mp4"
            audio_downloader = DownloaderWebSocket(url=youtube_track.video_url, destination=destination)
            await audio_downloader.set_websocket(websocket=websocket)
            thumbnail_downloader = Downloader(url=youtube_track.thumbnail_url)
            await asyncio.gather(audio_downloader.download(), thumbnail_downloader.download())
            await websocket.send_text(json.dumps({"type": "info", "info_message": f"Creating Track: {format}"}))
            mp4 = MP4.from_track(path=destination, track=youtube_track)
            await websocket.send_text(
                json.dumps({"type": "info", "info_message": f"Generating destination media {youtube_track.filename}"})
            )
            await mp4.save(thumbnail_downloader.buffer)
            file_url = f"/youtube/{youtube_track.filename}.mp4"
            await websocket.send_text(json.dumps({"type": "info", "info_message": "Done"}))
            await websocket.send_text(
                json.dumps({"type": "file_ready", "url": file_url, "filename": f"{youtube_track.filename}.mp4"})
            )

        await websocket.send_text(json.dumps({"type": "completed"}))
        break
