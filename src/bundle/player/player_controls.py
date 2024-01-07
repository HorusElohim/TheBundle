from enum import Enum

import bundle
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QSlider,
                               QWidget)

from . import styles

logger = bundle.getLogger(__name__)

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
        self.button.setStyleSheet(styles.BUTTON_STYLE)

        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setStyleSheet(styles.SLIDER_STYLE)

        self.label = QLabel("00:00 / 00:00")
        self.label.setStyleSheet(styles.LABEL_STYLE)

        # Speaker button
        self.speakerButton = QPushButton("🔊")
        self.speakerButton.clicked.connect(self.toggle_volume_slider)
        self.speakerButton.setStyleSheet(styles.BUTTON_STYLE)
        # Volume slider (initially hidden)
        self.volumeSlider = QSlider(Qt.Horizontal)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(100)
        self.volumeSlider.setMaximumWidth(self.parent().width() * 0.3)
        self.volumeSlider.hide()
        
        self.toggleQueueButton = QPushButton(">")
        self.toggleQueueButton.setMaximumWidth(28)

        layout = QHBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.timeline)
        layout.addWidget(self.label)
        layout.addWidget(self.speakerButton)
        layout.addWidget(self.volumeSlider)
        layout.addWidget(self.toggleQueueButton)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        logger.debug(f"constructed {bundle.core.Emoji.success}")

    def toggle_volume_slider(self):
        self.volumeSlider.setVisible(not self.volumeSlider.isVisible())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.volumeSlider.setMaximumWidth(self.parent().width() * 0.3)  # Adjust max width on resize
