import bundle
from PySide6.QtCore import QUrl
from .base import TrackBase
from ..medias import MP3, MP4


logger = bundle.getLogger(__name__)


@bundle.Data.dataclass
class TrackLocal(TrackBase):
    path: QUrl | bundle.Path = None

    def __post_init__(self):
        super().__post_init__()
        if self.path is None:
            raise ValueError("path cannot be None")
        if isinstance(self.path, QUrl):
            path = bundle.Path(self.path.toLocalFile())
        else:
            path = self.path
            self.path = QUrl.fromLocalFile(str(path))
        match path.suffix:
            case ".mp3":
                self.track = MP3.load(path)
            case ".mp4":
                self.track = MP4.load(path)
            case _:
                self.track = None
        logger.debug(f"constructed {bundle.core.Emoji.success}")
