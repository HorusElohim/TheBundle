from threading import Lock
import sys
import os
import subprocess
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import (
    QFileDialog,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

import bundle
import time

from .popup import warning_popup
from .controls import PlayerControls, ControlButton
from .engine import PlayerEngine
from .queue import PlayerQueue
from ..track import TrackBase
from .. import config

logger = bundle.getLogger(__name__)

MEDIA_STATUS_OK = [
    QMediaPlayer.MediaStatus.LoadingMedia,
    QMediaPlayer.MediaStatus.LoadedMedia,
    QMediaPlayer.MediaStatus.BufferedMedia,
    QMediaPlayer.MediaStatus.BufferingMedia,
]

MEDIA_STATUS_NOK = [QMediaPlayer.MediaStatus.NoMedia, QMediaPlayer.MediaStatus.EndOfMedia]


def format_time(ms):
    seconds = round(ms / 1000)
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


class Player(QWidget):
    def __init__(self):
        super().__init__()
        self._lock = Lock()
        self.engine = PlayerEngine(self)
        self.engine.player.durationChanged.connect(self.duration_changed)
        self.engine.player.mediaStatusChanged.connect(self.handle_media_status_changed)

        self.queue = PlayerQueue(self)
        self.queue.queueList.itemRemoved.connect(self.remove_track)
        self.queue.queueList.itemDoubleClicked.connect(self.play_track_at)

        self.controls = PlayerControls(self)
        self.controls.play_button.clicked.connect(self.toggle_play_pause)
        self.controls.next_button.clicked.connect(self.play_next_track)
        self.controls.previous_button.clicked.connect(self.play_previous_track)
        self.controls.timeline.sliderMoved.connect(self.set_position)
        self.controls.timer.timeout.connect(self.update_timeline)
        self.controls.volumeSlider.valueChanged.connect(self.set_volume)
        self.controls.shuffle_button.clicked.connect(self.queue.shuffle_tracks)
        self.controls.open_directory_button.clicked.connect(self.open_directory)

        self.queue.show()
        self.setup_ui()
        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def setup_ui(self):
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setContentsMargins(0, 0, 0, 0)

        playerWidget = QWidget()
        playerLayout = QVBoxLayout(playerWidget)
        playerLayout.addWidget(self.engine)
        playerLayout.setContentsMargins(0, 0, 0, 0)
        playerLayout.setSpacing(0)
        splitter.addWidget(playerWidget)
        splitter.addWidget(self.queue)

        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        mainLayout.addWidget(splitter)
        mainLayout.addWidget(self.controls)

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
        self.play()

    def handle_media_status_changed(self, status):
        logger.debug(f"handle_media_status_changed with {status=}")
        time.sleep(0.1)
        if status in MEDIA_STATUS_OK and not self.engine.video.isVisible():
            self.engine.stackedLayout.setCurrentWidget(self.engine.video)
            self.engine.imageLabel.hide()
            self.engine.video.show()
        elif status in MEDIA_STATUS_NOK and not self.engine.imageLabel.isVisible():
            self.engine.video.hide()
            self.engine.imageLabel.show()
            self.engine.stackedLayout.setCurrentWidget(self.engine.imageLabel)
            self.controls.play_button.setText(ControlButton.play.value)
            if status is QMediaPlayer.MediaStatus.EndOfMedia and self.queue.has_next():
                self.play_next_track()

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
        self.controls.play_button.setText(ControlButton.pause.value)
        self.controls.timer.start()

    def stop(self):
        logger.debug("stop")
        self.controls.timer.stop()
        self.engine.player.stop()
        self.engine.player.setSource(QUrl())
        self.controls.play_button.setText(ControlButton.play.value)

    def play(self):
        logger.debug("play")
        current_track = self.queue.get_current_track()
        if current_track:
            self.engine.play_track(current_track)
            self.controls.play_button.setText(ControlButton.pause.value)
            self.controls.timer.start()
        else:
            self.controls.play_button.setText(ControlButton.play.value)

    def pause(self):
        self.engine.player.pause()
        self.controls.play_button.setText(ControlButton.play.value)
        self.controls.timer.stop()
        logger.debug(ControlButton.pause.value)

    def set_volume(self, value):
        self.engine.audio.setVolume(value / 100)

    def play_next_track(self):
        self.queue.next_track()
        self.play()

    def play_previous_track(self):
        self.queue.previous_track()
        self.play()

    def add_track(self, track: TrackBase):
        self.queue.add_track(track)

    def set_position(self, position):
        self.engine.player.setPosition(position)

    def update_timeline(self):
        self.controls.timeline.setValue(self.engine.player.position())
        self.update_timeline_time_label()

    def duration_changed(self, duration):
        self.controls.timeline.setRange(0, duration)

    def update_timeline_time_label(self):
        current_time = self.engine.player.position()
        total_time = self.engine.player.duration()
        self.controls.label.setText(f"{format_time(current_time)} / {format_time(total_time)}")

    def get_current_player_status(self) -> QMediaPlayer.PlaybackState:
        return self.engine.player.playbackState()

    def open_directory(self):
        path = config.DATA_PATH
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":  # macOS
            subprocess.Popen(["open", path])
        else:  # Linux and other Unix-like OS
            subprocess.Popen(["xdg-open", path])
