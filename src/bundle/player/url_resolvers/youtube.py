import bundle
from pytube import YouTube
from . import Track, UrlType

logger = bundle.getLogger(__name__)


def format_time(seconds):
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


@bundle.Data.dataclass
class YoutubeURL(bundle.Task):
    def exec(self, url=None, *args, **kwds):
        try:
            if url is None:
                logger.error("url is None")
                raise ValueError(f"Please provide a valid {url=}")
            yt = YouTube(url)

            url_resolved = Track(source_url=url)
            url_resolved.url_type = UrlType.remote
            url_resolved.title = yt.title
            url_resolved.thumbnail_url = yt.thumbnail_url
            logger.debug(f"{yt.length=}")
            url_resolved.duration = format_time(yt.length)
            url_resolved.artist = yt.author

            audio_stream = yt.streams.filter(only_audio=True).first()
            url_resolved.audio_url = audio_stream.url if audio_stream else ""
            video_stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
            url_resolved.video_url = video_stream.url if video_stream else ""
            url_resolved.log_status()
        except Exception as e:
            logger.error(f"{bundle.core.Emoji.failed} Error {e}")
        return url_resolved

    def log_url_retrieving(self, message: str, url: str):
        if url:
            logger.debug(f"{message} {bundle.core.Emoji.success}")
        else:
            logger.error(f"{message} {bundle.core.Emoji.failed}")
