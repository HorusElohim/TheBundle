from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

import bundle
from .. import styles
from ...track import TrackBase

logger = bundle.getLogger(__name__)


def get_tooltips(track: TrackBase):
    tooltip = f"""
type: {track.class_type} | {track.track.class_type}
title: {track.track.title}
artist: {track.track.artist}
duration: {track.duration_str}
    """
    return tooltip


class QueueItemWidget(QWidget):
    def __init__(self, parent=None, track: TrackBase | None = None):
        super().__init__(parent)
        self.track = track
        self.setStyleSheet("background-color: black;")
        # Top-level horizontal layout
        layout = QHBoxLayout(self)
        # Thumbnail
        self.thumbnailLabel = QLabel()
        self.thumbnailLabel.setFixedSize(QSize(50, 50))
        self.thumbnailLabel.setStyleSheet(styles.THUMBNAIL_LABEL_STYLE)
        pixmap = QPixmap()
        if pixmap.loadFromData(self.track.track.thumbnail):
            self.thumbnailLabel.setPixmap(
                pixmap.scaled(self.thumbnailLabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        layout.addWidget(self.thumbnailLabel)

        # Vertical layout for title, artist, and duration
        detailsLayout = QVBoxLayout()

        # Title
        self.titleLabel = QLabel(track.track.title)
        self.titleLabel.setStyleSheet(styles.TITLE_LABEL_STYLE)
        detailsLayout.addWidget(self.titleLabel)

        # Artist
        self.artistLabel = QLabel(track.track.artist)
        self.artistLabel.setStyleSheet(styles.ARTIST_LABEL_STYLE)
        detailsLayout.addWidget(self.artistLabel)

        # Duration
        self.durationLabel = QLabel(track.duration_str)
        self.durationLabel.setStyleSheet(styles.DURATION_LABEL_STYLE)
        detailsLayout.addWidget(self.durationLabel)

        # Add the details layout to the main horizontal layout
        layout.addLayout(detailsLayout)

        self.setLayout(layout)
        self.setToolTip(get_tooltips(self.track))
        logger.debug("PlayerQueueItem constructed")

    def setSelectedStyle(self):
        self.titleLabel.setStyleSheet(styles.TITLE_LABEL_SELECTED_STYLE)
        self.artistLabel.setStyleSheet(styles.ARTIST_LABEL_SELECTED_STYLE)
        self.durationLabel.setStyleSheet(styles.DURATION_LABEL_SELECTED_STYLE)

    def resetStyle(self):
        self.titleLabel.setStyleSheet(styles.TITLE_LABEL_STYLE)
        self.artistLabel.setStyleSheet(styles.ARTIST_LABEL_STYLE)
        self.durationLabel.setStyleSheet(styles.DURATION_LABEL_STYLE)
