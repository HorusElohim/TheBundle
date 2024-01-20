import bundle
from PySide6.QtCore import QSize, Qt, QUrl, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QAudioDevice, QMediaDevices
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtNetwork import QNetworkRequest, QSslConfiguration, QSslSocket
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

from .. import config
from ..track import TrackBase

logger = bundle.getLogger(__name__)


class PlayerEngine(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
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
        self.player.errorOccurred.connect(self.handle_player_error)

        self.current_audio_device = QMediaDevices.defaultAudioOutput()
        self.audio_device_check_timer = QTimer(self)
        self.audio_device_check_timer.timeout.connect(self.check_audio_device)
        self.audio_device_check_timer.start(1250)  # Check every 5 seconds

        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def minimumSizeHint(self):
        # Provide a sensible minimum size
        return QSize(280, 260)  # Adjust as needed

    def _url_remote_request(self, url: QUrl):
        logger.debug("ssl request ...")
        req = QNetworkRequest(QUrl(url))
        sslConfig = QSslConfiguration.defaultConfiguration()
        sslConfig.setPeerVerifyMode(QSslSocket.PeerVerifyMode.AutoVerifyPeer)
        req.setSslConfiguration(sslConfig)
        logger.debug(f"ssl {bundle.core.Emoji.success}")

    def play_track(self, track: TrackBase):
        url = QUrl.fromLocalFile(str(track.track.path))
        logger.debug(f"play_track {url=}")
        self.player.setSource(url)
        self.player.play()

    def handle_player_error(self, error):
        if str(error) not in ["Error.FormatError"]:
            logger.error(f"Playback error: {error}")

    def check_audio_device(self):
        new_device = QMediaDevices.defaultAudioOutput()
        if new_device.description() != self.current_audio_device.description():
            logger.debug(
                f"Audio output device changed,\n{self.current_audio_device.description()} -> {new_device.description()}"
            )
            self.current_audio_device = new_device
            self.update_audio_output()

    def update_audio_output(self):
        logger.debug("update_audio_output")
        new_audio_output = QAudioOutput(self.current_audio_device, self)
        self.player.setAudioOutput(new_audio_output)
        self.audio = new_audio_output
