import bundle
from pytube import YouTube
from . import UrlResolved, UrlType

logger = bundle.getLogger(__name__)


@bundle.Data.dataclass
class YoutubeURL(bundle.Task):
    def exec(self, url=None, *args, **kwds):
        try:
            if url is None:
                logger.error("url is None")
                raise ValueError(f"Please provide a valid {url=}")
            url_resolved = UrlResolved(source_url=url)
            url_resolved.url_type = UrlType.remote
            yt = YouTube(url_resolved.source_url)
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
