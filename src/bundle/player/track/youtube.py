from bundle import data, logger
from pytube import YouTube, Playlist
from .base import TrackBase
from .database import DB
from ..medias import MP3, MP4

from tqdm import tqdm
import requests

log = logger.getLogger(__name__)


def resolve_youtube__playlist_urls(url: str) -> list[str]:
    return list(Playlist(url))


def download(url: str):
    try:
        log.debug(f"start downloading {url=}")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size_in_bytes = int(response.headers.get("content-length", 0))
        block_size = 4096
        progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)

        data = b""
        for data_chunk in response.iter_content(block_size):
            progress_bar.update(len(data_chunk))
            data += data_chunk
        progress_bar.close()

        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            log.error("ERROR, something went wrong")

        log.debug(f"downloaded data: {len(data) / 1024 / 1024} Mb")
        return data

    except Exception as e:
        log.error(f"Failed to download '{url=}'\n{e}")


class YoutubeURLS(data.Data):
    audio: str = ""
    video: str = ""
    thumbnail: str = ""


class TrackYoutube(TrackBase):
    url: str | None = None
    youtube_urls: list[YoutubeURLS] = data.Field(default_factory=list)

    @data.model_validator(mode="after")
    def post_init(self):
        if self.url is None:
            raise ValueError("url cannot be None")
        self.retrieve_youtube_info()
        if DB.has(self.track):
            self.path = DB.get(self.identifier)
            log.info(f"track already in db {self.identifier} -> {self.path}")
            self.track.load(self.path)
        else:
            self.download_track()

    def retrieve_youtube_info(self):
        status = True
        try:
            log.debug("started")
            yt = YouTube(self.url)
            audio_stream = yt.streams.filter(only_audio=True).first()
            video_stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("abr").desc().first()
            audio_url = audio_stream.url if audio_stream else ""
            video_url = video_stream.url if video_stream else ""
            self.youtube_urls = YoutubeURLS(audio=audio_url, video=video_url, thumbnail=yt.thumbnail_url)
            self.track = MP4(
                title=yt.title,
                artist=yt.author,
                duration=yt.length,
            )
        except Exception as e:
            status = False
            log.error(f"{e}")
        finally:
            log.debug(f"{logger.Emoji.status(status)}")

    def download_track(self, download_url_callback=download):
        try:
            log.debug("started")
            self.track.thumbnail = download_url_callback(self.youtube_urls.thumbnail)
            self.track.save(data=download_url_callback(self.youtube_urls.video))
            self.path = self.track.path
            log.info(f"track downloaded: {self.track.path}")

        except Exception as e:
            log.error(f"{logger.Emoji.failed} Error {e}")
