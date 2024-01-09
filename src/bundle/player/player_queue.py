from PySide6.QtCore import QObject, Qt, QUrl, Signal, QSize
from PySide6.QtGui import QColor, QMouseEvent, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QSslConfiguration, QSslSocket
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

import bundle

from .styles import ARTIST_LABEL_STYLE, DURATION_LABEL_STYLE, THUMBNAIL_LABEL_STYLE, TITLE_LABEL_STYLE
from .url_resolvers import Track

logger = bundle.getLogger(__name__)


class ImageDownloader(QObject):
    downloaded = Signal(QPixmap)

    def __init__(self, url):
        super().__init__()
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.on_download_finished)
        self.manager.sslErrors.connect(self.on_ssl_errors)
        req = QNetworkRequest(QUrl(url))
        sslConfig = QSslConfiguration.defaultConfiguration()
        sslConfig.setPeerVerifyMode(QSslSocket.VerifyNone)
        req.setSslConfiguration(sslConfig)
        self.manager.get(req)
        logger.debug("ImageDownloader constructed for URL: " + url)

    def on_ssl_errors(self, reply, errors):
        for error in errors:
            logger.error(f"SSL error: {error.errorString()}")

    def on_download_finished(self, reply):
        logger.debug("ImageDownloader on_download_finished triggered")
        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if reply.error() and status_code != 200:
            error_msg = f"Network error: {reply.errorString()}, Status Code: {status_code}"
            logger.error(error_msg)
            return
        logger.debug("Downloading image thumbnail from network")
        data = reply.readAll()
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            logger.debug("Image thumbnail downloaded successfully")
            self.downloaded.emit(pixmap)
        else:
            logger.debug("Failed to download image thumbnail")


class PlayerQueueItem(QWidget):
    def __init__(self, parent=None, track: Track | None = None):
        super().__init__(parent)
        self.track = track
        self.setStyleSheet("background-color: black;")
        # Top-level horizontal layout
        layout = QHBoxLayout(self)
        # Thumbnail
        self.thumbnailLabel = QLabel()
        self.thumbnailLabel.setFixedSize(QSize(50, 50))
        self.thumbnailLabel.setStyleSheet(THUMBNAIL_LABEL_STYLE)
        layout.addWidget(self.thumbnailLabel)
        self.imageDownloader = ImageDownloader(track.thumbnail_url)
        self.imageDownloader.downloaded.connect(self.set_thumbnail)

        # Vertical layout for title, artist, and duration
        detailsLayout = QVBoxLayout()

        # Title
        self.titleLabel = QLabel(track.title)
        self.titleLabel.setStyleSheet(TITLE_LABEL_STYLE)
        detailsLayout.addWidget(self.titleLabel)

        # Artist
        self.artistLabel = QLabel(track.artist)
        self.artistLabel.setStyleSheet(ARTIST_LABEL_STYLE)
        detailsLayout.addWidget(self.artistLabel)

        # Duration
        self.durationLabel = QLabel(track.duration)
        self.durationLabel.setStyleSheet(DURATION_LABEL_STYLE)
        detailsLayout.addWidget(self.durationLabel)

        # Add the details layout to the main horizontal layout
        layout.addLayout(detailsLayout)

        self.setLayout(layout)
        logger.debug("PlayerQueueItem constructed")

    def set_thumbnail(self, pixmap: QPixmap):
        self.thumbnailLabel.setPixmap(pixmap.scaled(self.thumbnailLabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class CustomListWidget(QListWidget):
    itemRemoved = Signal(int)  # Signal to indicate item removal with row index
    itemDoubleClicked = Signal(int)  # Signal to indicate item double-click with row index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._startPos = None
        self._currentItem = None
        self._originalBgColor = None  # Store the original background color
        self.itemSelectionChanged.connect(self.onSelectionChanged)
        self.setStyleSheet("background-color: black;")

    def onSelectionChanged(self):
        if self._isSwiping:
            # Clear selection during swiping
            self.clearSelection()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._startPos = event.pos()
            self._currentItem = self.itemAt(event.pos())
            if self._currentItem:
                self._originalBgColor = self._currentItem.background()  # Store original color
                self._currentItem.setSelected(False)  # Disable default selection highlight

        self._isSwiping = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton and self._startPos is not None:
            endPos = event.pos()
            dx = endPos.x() - self._startPos.x()

            if self._currentItem:
                fraction = min(dx / self.width(), 1)  # Fraction of the width
                color = QColor(240, 0, 0, int(255 * fraction))  # Adjust the alpha value
                self._currentItem.setBackground(color)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._startPos is not None:
            endPos = event.pos()
            dx = endPos.x() - self._startPos.x()

            if dx > 90:  # Threshold for swipe distance
                item = self.itemAt(self._startPos)
                if item:
                    row = self.row(item)
                    logger.debug(f"emitting idex to remove: {row}")
                    self.itemRemoved.emit(row)

        if self._currentItem:
            self._currentItem.setBackground(self._originalBgColor if self._originalBgColor else Qt.transparent)
        self._startPos = None
        self._currentItem = None
        super().mouseReleaseEvent(event)

        self._isSwiping = False
        self.clearSelection()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        item = self.itemAt(event.pos())
        if item:
            row = self.row(item)
            self.itemDoubleClicked.emit(row)  # Emit the itemDoubleClicked signal
        super().mouseDoubleClickEvent(event)


class PlayerQueue(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(55)
        self.setStyleSheet("background-color: black;")
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 5, 0)
        self.setLayout(self.mainLayout)
        self.queueList = CustomListWidget()
        self.mainLayout.addWidget(self.queueList)
        self.currentlyPlayingIndex = -1

    def clear(self):
        self.queueList.clear()
        self.currentlyPlayingIndex = -1

    def isEmpty(self):
        logger.debug("isEmpty")
        return self.queueList.count() == 0

    def get_current_track(self) -> Track | None:
        if 0 <= self.currentlyPlayingIndex < self.queueList.count():
            itemWidget = self.queueList.itemWidget(self.queueList.item(self.currentlyPlayingIndex))
            if isinstance(itemWidget, PlayerQueueItem):
                return itemWidget.track
        return None

    def get_current_track_index(self) -> int:
        return self.currentlyPlayingIndex

    def add_track(self, track: Track):
        logger.debug("add_track")
        itemWidget = PlayerQueueItem(self, track)
        listItem = QListWidgetItem(self.queueList)
        listItem.setSizeHint(itemWidget.sizeHint())
        self.queueList.addItem(listItem)
        self.queueList.setItemWidget(listItem, itemWidget)
        if self.queueList.count() == 1:
            self.select_track(0)

    def has_next(self) -> int:
        has_next = self.currentlyPlayingIndex < self.queueList.count() - 1
        logger.debug(f"has_next: {has_next}")
        return has_next

    def next_track(self):
        logger.debug("next_track")
        if self.queueList.count() > 0 and self.currentlyPlayingIndex < self.queueList.count() - 1:
            self.select_track(self.currentlyPlayingIndex + 1)
        else:
            logger.warning("no next_track")

    def previous_track(self):
        logger.debug("previous_track")
        if self.currentlyPlayingIndex > 0:
            self.reset_selection()
            if self.currentlyPlayingIndex > 1:
                self.select_track(self.currentlyPlayingIndex - 1)

    def remove_track(self, index: int):
        logger.debug(f"remove_track: {index}")
        if 0 <= index < self.queueList.count():
            self.queueList.takeItem(index)
            if self.currentlyPlayingIndex >= index:
                self.currentlyPlayingIndex -= 1

    def select_track(self, index: int):
        logger.debug(f"select_track: {index}")
        if index > self.queueList.count():
            logger.error(f"{index=} out of range")
        self.currentlyPlayingIndex = index
        self.queueList.item(index).setBackground(QColor(0, 0, 50, 10))

    def reset_selection(self):
        if self.currentlyPlayingIndex >= 0:
            self.queueList.item(self.currentlyPlayingIndex).setBackground(QColor(0, 0, 0, 0))
