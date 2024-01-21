from enum import Enum

import bundle
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QWidget

from . import styles
import logging

logger = logging.getLogger(__name__)


class ControlButton(Enum):
    play = "▶"
    pause = "="
    next = ">"
    previous = "<"
    audio = "🔊"
    shuffle = "🔀"
    open_directory = "📁"


class PlayerControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: black;")

        self.play_button = QPushButton(ControlButton.play.value)
        self.play_button.setStyleSheet(styles.BUTTON_STYLE)
        self.play_button.setToolTip("Play/Pause")

        self.next_button = QPushButton(ControlButton.next.value)
        self.next_button.setStyleSheet(styles.BUTTON_STYLE)
        self.next_button.setToolTip("Next track")

        self.previous_button = QPushButton(ControlButton.previous.value)
        self.previous_button.setStyleSheet(styles.BUTTON_STYLE)
        self.previous_button.setToolTip("Previous track")

        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setStyleSheet(styles.SLIDER_STYLE)

        self.label = QLabel("00:00 / 00:00")
        self.label.setStyleSheet(styles.LABEL_STYLE)

        # Speaker button
        self.speakerButton = QPushButton(ControlButton.audio.value)
        self.speakerButton.setStyleSheet(styles.BUTTON_STYLE)
        self.speakerButton.setToolTip("Open volume")
        self.speakerButton.clicked.connect(self.toggle_volume_slider)

        # Volume slider (initially hidden)
        self.volumeSlider = QSlider(Qt.Horizontal)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(100)
        self.volumeSlider.setMaximumWidth(self.parent().width() * 0.3)
        self.volumeSlider.hide()

        # Shuffle
        self.shuffle_button = QPushButton(ControlButton.shuffle.value)
        self.shuffle_button.setStyleSheet(styles.BUTTON_STYLE)
        self.shuffle_button.setToolTip("Shuffle the order of the tracks")

        # Open Directory button
        self.open_directory_button = QPushButton(ControlButton.open_directory.value)
        self.open_directory_button.setStyleSheet(styles.BUTTON_STYLE)
        self.open_directory_button.setToolTip("Open a directory")

        layout = QHBoxLayout()
        layout.addWidget(self.play_button)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.timeline)
        layout.addWidget(self.label)
        layout.addWidget(self.speakerButton)
        layout.addWidget(self.volumeSlider)
        layout.addWidget(self.shuffle_button)
        layout.addWidget(self.open_directory_button)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def toggle_volume_slider(self):
        self.volumeSlider.setVisible(not self.volumeSlider.isVisible())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.volumeSlider.setMaximumWidth(self.parent().width() * 0.3)
