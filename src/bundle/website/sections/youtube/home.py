import asyncio
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from bundle.core import data
from bundle.core.downloader import Downloader
from bundle.youtube.media import MP4
from bundle.youtube.pytube import resolve
from bundle.youtube.track import YoutubeTrackData

from ...common.downloader import DownloaderWebSocket
from ...common.sections import base_context, create_templates, get_logger, get_static_path, get_template_path
from ...common.websocket import WebSocketDataMixin

NAME = "youtube"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

MUSIC_PATH = Path(__file__).parent / "static"


router = APIRouter()
templates = create_templates(TEMPLATE_PATH)


class InfoMessage(data.Data, WebSocketDataMixin):
    type: Literal["info"] = "info"
    info_message: str


class CompletedMessage(data.Data, WebSocketDataMixin):
    type: Literal["completed"] = "completed"


class FileReadyMessage(data.Data, WebSocketDataMixin):
    type: Literal["file_ready"] = "file_ready"
    url: str
    filename: str
    format: str = data.Field(default="mp4")


class DownloadTrackRequest(data.Data, WebSocketDataMixin):
    youtube_url: str
    format: str = "mp4"

    @data.model_validator(mode="after")
    def normalize(self):
        self.youtube_url = self.youtube_url.strip()
        fmt = (self.format or "mp4").lower()
        self.format = fmt if fmt in {"mp3", "mp4"} else "mp4"
        return self


class TrackMetadata(YoutubeTrackData, WebSocketDataMixin):
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
            request_payload = await DownloadTrackRequest.receive(websocket)
        except WebSocketDisconnect:
            LOGGER.debug("YouTube websocket disconnected: %s", websocket.client)
            break
        except Exception as exc:
            LOGGER.warning("Invalid YouTube websocket payload: %s", exc)
            continue

        LOGGER.debug("received: %s", await request_payload.as_dict())
        youtube_url = request_payload.youtube_url
        requested_format = request_payload.format

        await InfoMessage(info_message="Resolving YouTube track").send(websocket)
        resolved_any = False
        async for youtube_track in resolve(youtube_url):
            if youtube_track is None or not youtube_track.is_resolved():
                await InfoMessage(info_message="Skipping unresolved entry from playlist").send(websocket)
                continue

            resolved_any = True
            track_metadata = TrackMetadata(**await youtube_track.as_dict())
            await track_metadata.send(websocket)

            destination = MUSIC_PATH / f"{youtube_track.filename}.mp4"
            audio_downloader = DownloaderWebSocket(url=youtube_track.video_url, destination=destination, websocket=websocket)
            thumbnail_downloader = Downloader(url=youtube_track.thumbnail_url)
            await asyncio.gather(audio_downloader.download(), thumbnail_downloader.download())

            await InfoMessage(info_message=f"Embedding metadata for {youtube_track.filename}").send(websocket)
            mp4 = MP4.from_track(path=destination, track=youtube_track)
            await mp4.save(thumbnail_downloader.buffer)

            served_path = mp4.path
            if requested_format == "mp3":
                await InfoMessage(info_message="Extracting MP3 audio").send(websocket)
                mp3 = await mp4.extract_mp3()
                served_path = mp3.path

            file_url = f"/youtube/{served_path.name}"
            await InfoMessage(info_message="Download ready").send(websocket)
            await FileReadyMessage(url=file_url, filename=served_path.name, format=requested_format).send(websocket)

        if not resolved_any:
            await InfoMessage(info_message="Unable to resolve any playable entries").send(websocket)

        await CompletedMessage().send(websocket)
