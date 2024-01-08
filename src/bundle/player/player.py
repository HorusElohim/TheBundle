from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

import bundle
import time

from . import config
from .player_popup import warning_popup
from .player_controls import PlayerControls, ControlButton
from .player_engine import PlayerEngine
from .player_queue import PlayerQueue

from .url_resolvers import get_url_resolved

logger = bundle.getLogger(__name__)


class BundlePlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.setGeometry(800, 180, 666, 666)
        self.resize(QSize(800, 666))
        self.setAcceptDrops(True)
        self.setWindowIcon(QIcon(str(config.ICON_PATH.absolute())))

        self.engine = PlayerEngine(self)
        self.engine.player.durationChanged.connect(self.duration_changed)
        self.engine.player.mediaStatusChanged.connect(self.handle_media_status_changed)

        self.controls = PlayerControls(self)
        self.controls.button.clicked.connect(self.toggle_play_pause)
        self.controls.timeline.sliderMoved.connect(self.set_position)
        self.controls.timer.timeout.connect(self.update_timeline)
        self.controls.volumeSlider.valueChanged.connect(self.set_volume)

        self.queue = PlayerQueue(self)
        self.queue.queueList.itemRemoved.connect(self.remove_track)
        self.queue.queueList.itemDoubleClicked.connect(self.play_track_at)

        self.queue.show()

        self.setup_ui()
        self.url_resolved = None
        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def setup_ui(self):
        # Create a horizontal splitter
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setContentsMargins(0, 0, 0, 0)

        # Create a widget to hold the player layout
        playerWidget = QWidget()
        playerLayout = QVBoxLayout(playerWidget)
        playerLayout.addWidget(self.engine)
        playerLayout.addWidget(self.controls)
        playerLayout.setContentsMargins(0, 0, 0, 0)
        playerLayout.setStretch(0, 1)  # Give video widget more space
        playerLayout.setStretch(1, 0)  # Minimal space for controls
        playerLayout.setSpacing(0)

        # Add playerWidget and PlayerQueue to the splitter
        splitter.addWidget(playerWidget)
        splitter.addWidget(self.queue)

        # Set the main layout of the window to contain the splitter
        mainLayout = QHBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(splitter)
        self.setLayout(mainLayout)

        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def remove_track(self, index: int):
        current_index = self.queue.get_current_track_index()
        logger.debug(f"remove_track {index=} with {current_index=}")
        self.queue.remove_track(index)
        if current_index == index:
            self.stop()

    def play_track_at(self, index: int):
        logger.debug(f"play_track_at: {index}")
        self.queue.select_track(index)
        self.stop()

    def handle_media_status_changed(self, status):
        logger.debug(f"handle_media_status_changed with {status=}")
        if (
            status
            in [
                QMediaPlayer.MediaStatus.LoadingMedia,
                QMediaPlayer.MediaStatus.LoadedMedia,
                QMediaPlayer.MediaStatus.BufferedMedia,
                QMediaPlayer.MediaStatus.BufferingMedia,
            ]
            and not self.engine.video.isVisible()
        ):
            logger.debug("show player")
            self.engine.stackedLayout.setCurrentWidget(self.engine.video)
            self.engine.imageLabel.hide()
            self.engine.video.show()
        elif (
            status in [QMediaPlayer.MediaStatus.NoMedia, QMediaPlayer.MediaStatus.EndOfMedia]
            and not self.engine.imageLabel.isVisible()
        ):
            self.engine.video.hide()
            self.engine.imageLabel.show()
            self.engine.stackedLayout.setCurrentWidget(self.engine.imageLabel)
            self.controls.button.setText(ControlButton.play.value)
            logger.debug("show logo")

        time.sleep(0.1)
        self.check_next_in_queue(status)

    def check_next_in_queue(self, status):
        logger.debug(f"check_next_in_queue with {status=}")
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.queue.has_next():
                self.play()
            else:
                warning_popup(self, "Queue is empty", "No more URLs to play")
                self.controls.button.setText(ControlButton.play.value)
        if self.engine.player.playbackState() is QMediaPlayer.PlaybackState.StoppedState:
            logger.debug("check_next_in_queue need to play")
            self.play()

    def toggle_play_pause(self):
        state = self.engine.player.playbackState()
        logger.debug(f"toggle_play_pause {state=}")
        match state:
            case QMediaPlayer.PlaybackState.PlayingState:
                self.pause()
            case QMediaPlayer.PlaybackState.PausedState:
                self.resume()
            case QMediaPlayer.PlaybackState.StoppedState:
                self.play()

    def resume(self):
        logger.debug("resume")
        self.engine.player.play()
        self.controls.button.setText(ControlButton.pause.value)
        self.controls.timer.start()

    def stop(self):
        logger.debug("stop")
        self.controls.timer.stop()
        self.engine.player.stop()
        self.engine.player.setSource(QUrl())
        self.controls.button.setText(ControlButton.play.value)

    def play(self):
        logger.debug("play")
        current_track = self.queue.get_current_track()
        if current_track and self.engine.play_track(current_track):
            self.controls.button.setText(ControlButton.pause.value)
            self.controls.timer.start()
        else:
            self.controls.button.setText(ControlButton.play.value)

    def play_track(self):
        logger.debug("play_track")
        current_track = self.queue.get_current_track()
        logger.debug(f"{current_track=}")
        if current_track:
            if self.engine.play_track(current_track):
                self.controls.button.setText(ControlButton.pause.value)
                self.controls.timer.start()
            else:
                warning_popup(self, "Playback Error", "Cannot play the selected URL")
                self.controls.button.setText(ControlButton.play.value)
        else:
            warning_popup(self, "Queue is empty", "No more URLs to play")

    def pause(self):
        self.engine.player.pause()
        self.controls.button.setText(ControlButton.play.value)
        self.controls.timer.stop()
        logger.debug(ControlButton.pause.value)

    def set_volume(self, value):
        self.engine.audio.setVolume(value / 100)

    def play_next_track(self):
        self.queue.next_track()
        self.play_track()

    def play_previous_track(self):
        self.queue.previous_track()
        self.play_track()

    def add_track(self, url):
        logger.debug(f"add_track {url=}")
        url_resolved = get_url_resolved(url)
        if url_resolved:
            self.queue.add_track(url_resolved)
        logger.debug(f"{self.get_current_player_status()=}")
        if self.get_current_player_status() is QMediaPlayer.PlaybackState.StoppedState:
            self.play_track()

    def dropEvent(self, event):
        logger.debug("drop")
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            logger.debug("drop has url")
            url = mimeData.urls()[0]
            self.add_track(url)

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
                self.add_track(clipboard_url)

    def get_current_player_status(self) -> QMediaPlayer.PlaybackState:
        return self.engine.player.playbackState()
