"""YouTube page routes and websocket download/probe workflow."""

import asyncio
from pathlib import Path
from typing import Literal

from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from bundle.core import data
from bundle.core.downloader import Downloader
from bundle.website.core.downloader import DownloaderWebSocket
from bundle.website.core.templating import PageModule, base_context
from bundle.website.core.ws_messages import WebSocketDataMixin
from bundle.youtube import media
from bundle.youtube.media import MP4
from bundle.youtube.pytube import probe, resolve
from bundle.youtube.track import YoutubeResolveOptions, YoutubeStreamOption, YoutubeTrackData

page = PageModule(
    __file__,
    name="YouTube",
    description="Resolve and download tracks directly into The Bundle workbench.",
)

MUSIC_PATH = Path(__file__).parent / "static"


class InfoMessage(data.Data, WebSocketDataMixin):
    """UI status message sent over websocket."""

    type: Literal["info"] = "info"
    info_message: str


class CompletedMessage(data.Data, WebSocketDataMixin):
    """Signal that the current probe/download cycle is finished."""

    type: Literal["completed"] = "completed"


class FileReadyMessage(data.Data, WebSocketDataMixin):
    """Provide a ready-to-download file URL to the client."""

    type: Literal["file_ready"] = "file_ready"
    url: str
    filename: str
    format: str = data.Field(default="mp4")


class DownloadTrackRequest(data.Data, WebSocketDataMixin):
    """Client request payload for YouTube probe/download actions."""

    youtube_url: str
    format: str = "mp4"
    action: Literal["probe", "download"] = "probe"
    itag: int | None = None

    @data.model_validator(mode="after")
    def normalize(self):
        """Normalize URL and constrain action/format to supported values."""
        self.youtube_url = self.youtube_url.strip()
        fmt = (self.format or "mp4").lower()
        self.format = fmt if fmt in {"mp3", "mp4"} else "mp4"
        self.action = self.action if self.action in {"probe", "download"} else "probe"
        return self


class TrackMetadata(YoutubeTrackData, WebSocketDataMixin):
    """Resolved track metadata payload for the frontend."""

    type: Literal["metadata"] = "metadata"


class QualityOptionsMessage(data.Data, WebSocketDataMixin):
    """Optional payload for available quality selections."""

    type: Literal["qualities"] = "qualities"
    options: list[YoutubeStreamOption] = data.Field(default_factory=list)


def _pick_simple_mp4_option(track: YoutubeTrackData) -> YoutubeStreamOption | None:
    """Return preferred progressive MP4 option (360p first, then first MP4)."""
    preferred = next(
        (opt for opt in track.video_streams if opt.progressive and opt.mime_type == "video/mp4" and opt.resolution == "360p"),
        None,
    )
    if preferred:
        return preferred
    return next((opt for opt in track.video_streams if opt.progressive and opt.mime_type == "video/mp4"), None)


def _simple_quality_options(track: YoutubeTrackData) -> list[YoutubeStreamOption]:
    """Expose simplified frontend options (single MP4 plus derived MP3)."""
    mp4_option = _pick_simple_mp4_option(track)
    if not mp4_option:
        return []
    mp3_option = mp4_option.model_copy(
        update={
            "kind": "audio",
            "resolution": "",
            "abr": "MP3 (extracted)",
            "fps": 0,
            "mime_type": "audio/mpeg",
            "progressive": False,
            "filesize": 0,
        }
    )
    return [mp4_option, mp3_option]


def _existing_served_path(filename: str, requested_format: str) -> Path | None:
    """Return existing output path if a requested format is already available."""
    mp4_path = MUSIC_PATH / f"{filename}.mp4"
    mp3_path = MUSIC_PATH / f"{filename}.mp3"
    if requested_format == "mp4" and mp4_path.exists():
        return mp4_path
    if requested_format == "mp3" and mp3_path.exists():
        return mp3_path
    return None


@page.router.get("/youtube", response_class=HTMLResponse)
async def youtube(request: Request):
    """Render the YouTube page."""
    return page.templates.TemplateResponse(request, "youtube.html", base_context(request))


@page.router.websocket("/ws/youtube/download_track")
async def download_track(websocket: WebSocket):
    """Handle probe/download commands and stream progress/results to the UI."""
    await websocket.accept()
    page.logger.debug("callback called from websocket url: %s", websocket.url)
    while True:
        try:
            request_payload = await DownloadTrackRequest.receive(websocket)
        except WebSocketDisconnect:
            page.logger.debug("YouTube websocket disconnected: %s", websocket.client)
            break
        except Exception as exc:
            page.logger.warning("Invalid YouTube websocket payload: %s", exc)
            continue

        page.logger.debug("received: %s", await request_payload.as_dict())
        youtube_url = request_payload.youtube_url
        requested_format = request_payload.format

        if request_payload.action == "probe":
            await InfoMessage(info_message="Resolving YouTube track").send(websocket)
            resolved_any = False
            async for youtube_track in probe(youtube_url):
                if youtube_track is None or not youtube_track.is_resolved():
                    await InfoMessage(info_message="Skipping unresolved entry from playlist").send(websocket)
                    continue

                resolved_any = True
                track_metadata = TrackMetadata(**await youtube_track.as_dict())
                await track_metadata.send(websocket)
                simple_options = _simple_quality_options(youtube_track)
                if not simple_options:
                    await InfoMessage(info_message="No supported progressive MP4 stream found for this video").send(websocket)
                    continue
                break

            if not resolved_any:
                await InfoMessage(info_message="Unable to resolve any playable entries").send(websocket)

            await CompletedMessage().send(websocket)
            continue

        await InfoMessage(info_message="Resolving track").send(websocket)
        resolved_any = False
        async for base_track in resolve(youtube_url, options=YoutubeResolveOptions(best=True)):
            if base_track is None or not base_track.is_resolved():
                await InfoMessage(info_message="Skipping unresolved entry from playlist").send(websocket)
                continue

            existing_path = _existing_served_path(base_track.filename, requested_format)
            if existing_path:
                resolved_any = True
                await InfoMessage(info_message="Using existing local file").send(websocket)
                file_url = f"/youtube/{existing_path.name}"
                await FileReadyMessage(url=file_url, filename=existing_path.name, format=requested_format).send(websocket)
                continue

            mp4_option = _pick_simple_mp4_option(base_track)
            download_url = (mp4_option.url or "").strip() if mp4_option else ""
            if not download_url:
                download_url = base_track.video_url.strip()
            if not download_url:
                await InfoMessage(info_message="No downloadable MP4 stream found for this video").send(websocket)
                continue

            resolved_any = True
            destination = MUSIC_PATH / f"{base_track.filename}.mp4"
            thumbnail_downloader = Downloader(url=base_track.thumbnail_url)
            video_downloader = DownloaderWebSocket(
                url=download_url,
                destination=destination,
                websocket=websocket,
            )
            video_ok, thumb_ok = await asyncio.gather(video_downloader.download(), thumbnail_downloader.download())
            if not video_ok or not destination.exists():
                detail = video_downloader.error_message or "unknown reason"
                await InfoMessage(info_message=f"Video download failed before processing: {detail}").send(websocket)
                continue
            if not media.is_mp4_container(destination):
                destination.unlink(missing_ok=True)
                await InfoMessage(info_message="Download failed: stream is not a valid MP4 container").send(websocket)
                continue

            if requested_format == "mp3":
                try:
                    await InfoMessage(info_message=f"Extracting MP3 for {base_track.filename}").send(websocket)
                    mp3_thumbnail = thumbnail_downloader.buffer if thumb_ok else None
                    mp3 = await media.extract_mp3_from_path(destination, base_track, mp3_thumbnail)
                    destination.unlink(missing_ok=True)
                    served_path = mp3.path
                except Exception as exc:
                    await InfoMessage(info_message=f"MP3 conversion failed: {exc}").send(websocket)
                    destination.unlink(missing_ok=True)
                    continue
            else:
                try:
                    await InfoMessage(info_message=f"Embedding metadata for {base_track.filename}").send(websocket)
                    mp4 = MP4.from_track(path=destination, track=base_track)
                    mp4_thumbnail = thumbnail_downloader.buffer if thumb_ok else None
                    await mp4.save(mp4_thumbnail)
                    served_path = mp4.path
                except Exception as exc:
                    await InfoMessage(info_message=f"MP4 tagging failed: {exc}").send(websocket)
                    continue

            file_url = f"/youtube/{served_path.name}"
            await InfoMessage(info_message="Download ready").send(websocket)
            await FileReadyMessage(url=file_url, filename=served_path.name, format=requested_format).send(websocket)

        if not resolved_any:
            await InfoMessage(info_message="Unable to resolve any playable entries").send(websocket)

        await CompletedMessage().send(websocket)
