import bundle
from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtNetwork import QNetworkRequest, QSslConfiguration, QSslSocket
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

from . import config
from .player_popup import critical_popup
from .url_resolvers import UrlResolved, UrlType

logger = bundle.getLogger(__name__)


class PlayerEngine(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.video = QVideoWidget(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)

        self.imageLabel = QLabel(self)
        self.imageLabel.setPixmap(QPixmap(str(config.IMAGE_PATH.absolute())))
        self.imageLabel.setScaledContents(True)
        self.imageLabel.setAlignment(Qt.AlignCenter)

        # Set up the layout
        self.stackedLayout = QStackedLayout(self)
        self.stackedLayout.addWidget(self.video)
        self.stackedLayout.addWidget(self.imageLabel)
        # Remove margins and spacing
        self.stackedLayout.setContentsMargins(0, 0, 0, 0)
        self.stackedLayout.setSpacing(0)
        self.stackedLayout.setCurrentWidget(self.imageLabel)
        
        self.setLayout(self.stackedLayout)
        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def minimumSizeHint(self):
        # Provide a sensible minimum size
        return QSize(280, 260)  # Adjust as needed

    def _url_remote_request(self, url: QUrl):
        req = QNetworkRequest(QUrl(url))
        sslConfig = QSslConfiguration.defaultConfiguration()
        sslConfig.setPeerVerifyMode(QSslSocket.VerifyNone)
        req.setSslConfiguration(sslConfig)
        logger.debug(f"ssl {bundle.core.Emoji.success}")

    def play_url(self, url: UrlResolved):
        should_play = True
        match url.url_type:
            case UrlType.remote:
                url = QUrl(url.video_url)
                self._url_remote_request(url)
                self.player.setSource(url)
                logger.debug(f"remote {bundle.core.Emoji.success}")
            case UrlType.local:
                url = QUrl(url.video_url)
                self.player.setSource(url)
                logger.debug(f"local {bundle.core.Emoji.success}")
            case _:
                critical_popup(self, "Unknown URL", f"{url=}")
                should_play = False
        if should_play:
            self.player.play()
        return should_play
