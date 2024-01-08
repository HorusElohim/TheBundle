from enum import Enum

from PySide6.QtCore import QSize, Qt
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
        self.setGeometry(600, 180, 666, 666)
        self.resize(QSize(666, 666))
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

        # Optional: Set the initial sizes or proportion of the splitter
        splitter.setSizes([400, 200])  # Adjust these values as needed

        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def handle_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            logger.debug("show player")
            self.engine.stackedLayout.setCurrentWidget(self.engine.video)
        elif status in [QMediaPlayer.MediaStatus.NoMedia, QMediaPlayer.MediaStatus.EndOfMedia]:
            self.engine.stackedLayout.setCurrentWidget(self.engine.imageLabel)
            logger.debug("show image")

        self.check_next_in_queue(status)

    def check_next_in_queue(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.queue.currentlyPlayingIndex < self.queue.queueList.count() - 1:
                self.queue.highlight_next_item()
                self.play()

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
        # Check if there is a URL to play in the queue
        if self.queue.currentlyPlayingIndex < self.queue.queueList.count():
            current_url = self.queue.get_current_url()
            if current_url and self.engine.play_url(current_url):
                self.controls.button.setText(ControlButton.pause.value)
                self.controls.timer.start()
            else:
                self.controls.button.setText(ControlButton.play.value)
                warning_popup(self, "Playback Error", "Cannot play the selected URL")
        else:
            warning_popup(self, "Queue is empty", "No more URLs to play")
            self.controls.button.setText(ControlButton.play.value)

    def pause(self):
        self.engine.player.pause()
        self.controls.button.setText(ControlButton.play.value)
        self.controls.timer.stop()
        logger.debug(ControlButton.pause.value)

    def set_volume(self, value):
        self.engine.audio.setVolume(value / 100)

    def set_url(self, url):
        logger.debug(f"set {url=}")
        self.url_resolved = get_url_resolved(url)
        self.queue.add_url(self.url_resolved)
        if self.queue.isEmpty():
            self.queue.highlight_next_item()
        logger.debug(f"resolved\n{self.url_resolved}")

    def dropEvent(self, event):
        logger.debug("drop")
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            logger.debug("drop has url")
            url = mimeData.urls()[0]
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
