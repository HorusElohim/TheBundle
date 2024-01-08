import bundle

from enum import Enum
from PySide6.QtCore import QUrl


class UrlType(Enum):
    remote = "remote"
    local = "local"
    unknown = "unknown"


@bundle.Data.dataclass
class UrlResolved(bundle.Data.Json):
    url_type: UrlType = UrlType.unknown
    source_url: str = bundle.Data.field(default_factory=str)
    audio_url: str = bundle.Data.field(default_factory=str)
    video_url: str = bundle.Data.field(default_factory=str)
    thumbnail_url: str = bundle.Data.field(default_factory=str)
    title: str = bundle.Data.field(default_factory=str) 
    duration: str = bundle.Data.field(default_factory=str)
    artist: str = bundle.Data.field(default_factory=str)


    def log_status(self):
        def _url_status(message: str, url: str):
            if url:
                logger.debug(f"{message} {bundle.core.Emoji.success}")
            else:
                logger.error(f"{message} {bundle.core.Emoji.failed}")

        _url_status("source", self.source_url)
        _url_status("audio", self.audio_url)
        _url_status("video", self.video_url)
        _url_status("thumbnail", self.video_url)


logger = bundle.getLogger(__name__)

from .youtube import YoutubeURL


def resolve_url_type(url: str | QUrl) -> UrlType:
    match url:
        case str():
            if url.startswith("http://") or url.startswith("https://"):
                return UrlType.remote
            else:
                return UrlType.local
        case QUrl():
            return UrlType.local
        case _:
            return UrlType.unknown


def get_url_resolved(url: str | QUrl) -> UrlResolved:
    logger.debug("resolving: %s", url)
    url_type = resolve_url_type(url)
    logger.debug("url type '%s'", url_type.value)
    match url_type:
        case UrlType.remote:
            if "yout" in url:
                return YoutubeURL()(url)
            return UrlResolved(source_url=url, audio_url=url, video_url=url, url_type=url_type)
        case UrlType.local:
            return UrlResolved(source_url=url, audio_url=url, video_url=url, url_type=url_type)
        case UrlType.unknown:
            logger.warning("unknown url source")
            return UrlResolved(source_url=url, audio_url=url, video_url=url, url_type=url_type)
