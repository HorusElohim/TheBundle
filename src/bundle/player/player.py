from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QStackedLayout,
)
from PySide6.QtNetwork import QNetworkRequest, QSslConfiguration, QSslSocket
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import QUrl, Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QIcon
from pytube import YouTube
from enum import Enum
import bundle
import sys


player_path = bundle.Path(__file__).parent
logger = bundle.setup_logging(name="bundle_player", level=10)
IMAGE_PATH = player_path / "thebundleplayer.png"
ICON_PATH = player_path / "thebundle_icon.png"


BUTTON_STYLE = """
QPushButton {
    color: white;
    background-color: rgba(0, 0, 0, 0); /* No background */
    border: none;
    font-size: 16px;
    font-weight: bold;
    font-family: 'Arial';
}
QPushButton:hover {
    color: #AAAAAA; /* Light grey on hover */
}
"""

SLIDER_STYLE = """
QSlider::groove:horizontal {
    height: 8px;
    background: rgba(255, 255, 255, 50);
    margin: 2px 0;
}
QSlider::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #5e81ac, stop:1 #88c0d0);
    border: 1px solid #5e81ac;
    width: 18px;
    margin: -2px 0;
    border-radius: 9px;
    opacity: 0.7;
}
QSlider::add-page:horizontal {
    background: rgba(255, 255, 255, 28);
}
QSlider::sub-page:horizontal {
    background: rgba(0, 120, 215, 100);
}
"""

LABEL_STYLE = """
QLabel {
    color: white;
    font-size: 12px;
    font-family: 'Arial';
    background-color: rgba(0, 0, 0, 0); /* No background */
}
"""


def warning_popup(parent, title, message):
    QMessageBox.warning(
        parent,
        title,
        message,
        buttons=QMessageBox.Ok,
        defaultButton=QMessageBox.Ok,
    )


def critical_popup(parent, title, message):
    QMessageBox.critical(
        parent,
        title,
        message,
        buttons=QMessageBox.Ok,
        defaultButton=QMessageBox.Ok,
    )


@bundle.Data.dataclass
class BundleParseYoutubeMusicURL(bundle.Task):
    url: str = bundle.Data.field(default_factory=str)

    def exec(self, url=None, *args, **kwds):
        try:
            if url:
                self.url = url
            yt = YouTube(self.url)
            audio_stream = yt.streams.filter(only_audio=True).first()
            audio_url = audio_stream.url if audio_stream else None
            video_stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
            video_url = video_stream.url if video_stream else None
            if video_url:
                logger.debug(f"{bundle.core.Emoji.success}")
            else:
                logger.error(f"{bundle.core.Emoji.failed}")
        except Exception as e:
            logger.error(f"{bundle.core.Emoji.failed} Error {e}")
        return audio_url, video_url


class UrlType(Enum):
    remote = "remote"
    local = "local"
    unknown = "unknown"


class ControlButton(Enum):
    play = "▶"
    pause = "="


class PlayerControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: black;")

        self.button = QPushButton(ControlButton.play.value)
        self.button.setStyleSheet(BUTTON_STYLE)

        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setStyleSheet(SLIDER_STYLE)

        self.label = QLabel("00:00 / 00:00")
        self.label.setStyleSheet(LABEL_STYLE)

        # Speaker button
        self.speakerButton = QPushButton("🔊")
        self.speakerButton.clicked.connect(self.toggle_volume_slider)
        self.speakerButton.setStyleSheet(BUTTON_STYLE)
        # Volume slider (initially hidden)
        self.volumeSlider = QSlider(Qt.Horizontal)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(100)
        self.volumeSlider.setMaximumWidth(self.parent().width() * 0.3)
        self.volumeSlider.hide()

        layout = QHBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.timeline)
        layout.addWidget(self.label)
        layout.addWidget(self.speakerButton)
        layout.addWidget(self.volumeSlider)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def toggle_volume_slider(self):
        self.volumeSlider.setVisible(not self.volumeSlider.isVisible())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.volumeSlider.setMaximumWidth(self.parent().width() * 0.3)  # Adjust max width on resize


class PlayerEngine(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.video = QVideoWidget(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)

        self.imageLabel = QLabel(self)
        self.imageLabel.setPixmap(QPixmap(str(IMAGE_PATH.absolute())))
        self.imageLabel.setScaledContents(True)
        self.imageLabel.setAlignment(Qt.AlignCenter)

        # Set up the layout
        self._layout = QStackedLayout(self)
        self._layout.addWidget(self.video)
        self._layout.addWidget(self.imageLabel)

        self.setLayout(self._layout)

        # Remove margins and spacing
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.setCurrentWidget(self.imageLabel)

        self.player.mediaStatusChanged.connect(self.handle_status_change)
        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def minimumSizeHint(self):
        # Provide a sensible minimum size
        return QSize(280, 260)  # Adjust as needed

    def handle_status_change(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            logger.debug("show player")
            self._layout.setCurrentWidget(self.video)
        elif status in [QMediaPlayer.MediaStatus.NoMedia, QMediaPlayer.MediaStatus.EndOfMedia]:
            self._layout.setCurrentWidget(self.imageLabel)
            logger.debug("show image")

    def _url_resolver(self, url: str | QUrl) -> UrlType:
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

    def _url_remote_request(self, url: QUrl):
        req = QNetworkRequest(QUrl(url))
        sslConfig = QSslConfiguration.defaultConfiguration()
        sslConfig.setPeerVerifyMode(QSslSocket.VerifyNone)
        req.setSslConfiguration(sslConfig)
        logger.debug(f"ssl {bundle.core.Emoji.success}")

    def play_url(self, url: str | QUrl):
        url_type = self._url_resolver(url)
        should_play = True
        match url_type:
            case UrlType.remote:
                url = QUrl(url)
                self._url_remote_request(url)
                self.player.setSource(url)
                logger.debug(f"remote {bundle.core.Emoji.success}")
            case UrlType.local:
                self.mediaPlayer.setSource(QUrl.fromLocalFile(self.url))
                logger.debug(f"local {bundle.core.Emoji.success}")
            case _:
                critical_popup(self, "Unknown URL", f"{url=}")
                should_play = False
        if should_play:
            self.player.play()
        return should_play


class BundlePlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TheBundle Player")
        self.setGeometry(600, 180, 666, 666)
        self.resize(QSize(666, 666))
        self.setAcceptDrops(True)
        self.setWindowIcon(QIcon(str(ICON_PATH.absolute())))
        self.engine = PlayerEngine(self)
        self.engine.player.durationChanged.connect(self.duration_changed)

        self.controls = PlayerControls(self)
        self.controls.button.clicked.connect(self.toggle_play_pause)
        self.controls.timeline.sliderMoved.connect(self.set_position)
        self.controls.timer.timeout.connect(self.update_timeline)
        self.controls.volumeSlider.valueChanged.connect(self.set_volume)
        self.setup_ui()
        self.url = None
        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.engine)
        layout.addWidget(self.controls)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStretch(0, 1)  # Give video widget more space
        layout.setStretch(1, 0)  # Minimal space for controls
        layout.setSpacing(0)
        self.setLayout(layout)

    def toggle_play_pause(self):
        match self.engine.player.playbackState():
            case QMediaPlayer.PlaybackState.PlayingState:
                self.pause()
            case QMediaPlayer.PlaybackState.PausedState:
                self.resume()
            case _:
                self.play()

    def resume(self):
        self.engine.player.play()
        self.controls.button.setText(ControlButton.pause.value)
        self.controls.timer.start()

    def play(self):
        if self.url is not None:
            if self.engine.play_url(self.url):
                button_label = ControlButton.pause.value
                self.controls.timer.start()
            else:
                button_label = ControlButton.play.value
            self.controls.button.setText(button_label)
        else:
            warning_popup(self, "URL is not set", "Please drop a URL before playing")

    def pause(self):
        self.engine.player.pause()
        self.controls.button.setText(ControlButton.play.value)
        self.controls.timer.stop()
        logger.debug(ControlButton.pause.value)

    def set_volume(self, value):
        self.engine.audio.setVolume(value / 100)

    def set_url(self, url):
        if "yout" in url:
            url = self.resolve_youtube_url(url)
        self.url = url
        logger.debug(f"set {url=}")

    def dragEnterEvent(self, event):
        logger.debug("drag")
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def resolve_youtube_url(self, url):
        _, video_url = BundleParseYoutubeMusicURL(url=url)()
        return video_url

    def dropEvent(self, event):
        logger.debug("drop")
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            logger.debug("drop has url")
            url = mimeData.urls()[0].toString()
            self.set_url(url)
            self.play()

    def set_position(self, position):
        self.engine.player.setPosition(position)

    def update_timeline(self):
        self.controls.timeline.setValue(self.engine.player.position())
        self.update_label()

    def duration_changed(self, duration):
        self.controls.timeline.setRange(0, duration)

    def update_label(self):
        current_time = self.engine.player.position()
        total_time = self.engine.player.duration()
        self.controls.label.setText(f"{self.format_time(current_time)} / {self.format_time(total_time)}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    @staticmethod
    def format_time(ms):
        seconds = round(ms / 1000)
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_V and (event.modifiers() & Qt.ControlModifier):
            clipboard = QApplication.clipboard()
            clipboard_url = clipboard.text()
            if clipboard_url:
                self.set_url(clipboard_url)
                self.play()


def main():
    app = QApplication(sys.argv)
    app.setStyle("fusion")
    window = BundlePlayer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
