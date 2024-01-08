from PySide6.QtWidgets import QWidget, QListWidget, QVBoxLayout
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtCore import QUrl, QObject, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QListWidgetItem
from PySide6.QtNetwork import QNetworkRequest, QSslConfiguration, QSslSocket
from PySide6.QtGui import QPixmap, QColor, QMouseEvent
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtCore import Qt
import bundle
from .url_resolvers import UrlResolved
from .styles import THUMBNAIL_LABEL_STYLE, TITLE_LABEL_STYLE, ARTIST_LABEL_STYLE, DURATION_LABEL_STYLE

logger = bundle.getLogger(__name__)


class ImageDownloader(QObject):
    downloaded = Signal(QPixmap)

    def __init__(self, url, label):
        super().__init__()
        self.label = label
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
            self.label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio))
        else:
            logger.debug("Failed to download image thumbnail")


class PlayerQueueItem(QWidget):
    def __init__(self, urlResolved: UrlResolved):
        super().__init__()
        self.urlResolved = urlResolved

        # Top-level horizontal layout
        layout = QHBoxLayout(self)

        # Thumbnail
        self.thumbnailLabel = QLabel()
        self.thumbnailLabel.setStyleSheet(THUMBNAIL_LABEL_STYLE)
        layout.addWidget(self.thumbnailLabel)
        self.imageDownloader = ImageDownloader(urlResolved.thumbnail_url, self.thumbnailLabel)

        # Vertical layout for title, artist, and duration
        detailsLayout = QVBoxLayout()

        # Title
        self.titleLabel = QLabel(urlResolved.title)
        self.titleLabel.setStyleSheet(TITLE_LABEL_STYLE)
        detailsLayout.addWidget(self.titleLabel)

        # Artist
        self.artistLabel = QLabel(urlResolved.artist)
        self.artistLabel.setStyleSheet(ARTIST_LABEL_STYLE)
        detailsLayout.addWidget(self.artistLabel)

        # Duration
        self.durationLabel = QLabel(urlResolved.duration)
        self.durationLabel.setStyleSheet(DURATION_LABEL_STYLE)
        detailsLayout.addWidget(self.durationLabel)

        # Add the details layout to the main horizontal layout
        layout.addLayout(detailsLayout)

        self.setLayout(layout)
        logger.debug("PlayerQueueItem constructed")


class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._startPos = None
        self._currentItem = None
        self._originalBgColor = None  # Store the original background color
        self.itemSelectionChanged.connect(self.onSelectionChanged)

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
                fraction = min(abs(dx) / self.width(), 1)  # Fraction of the width
                color = QColor(255, 0, 0, int(255 * fraction))  # Adjust the alpha value
                self._currentItem.setBackground(color)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._startPos is not None:
            endPos = event.pos()
            dx = endPos.x() - self._startPos.x()

            if abs(dx) > 100:  # Threshold for swipe distance
                item = self.itemAt(self._startPos)
                if item:
                    row = self.row(item)
                    self.takeItem(row)  # Remove the item from the list
        

        if self._currentItem:
            self._currentItem.setBackground(self._originalBgColor if self._originalBgColor else Qt.transparent)
        self._startPos = None
        self._currentItem = None
        super().mouseReleaseEvent(event)
        
        self._isSwiping = False
        self.clearSelection()


class PlayerQueue(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(170)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 5, 0)
        self.setLayout(self.layout)
        self.queueList = CustomListWidget()
        self.layout.addWidget(self.queueList)
        self.currentlyPlayingIndex = -1

    def add_url(self, url: UrlResolved):
        logger.debug("add_url")
        itemWidget = PlayerQueueItem(url)
        listItem = QListWidgetItem(self.queueList)
        listItem.setSizeHint(itemWidget.sizeHint())
        self.queueList.addItem(listItem)
        self.queueList.setItemWidget(listItem, itemWidget)
        if self.queueList.count() == 1:
            self.queueList.setItemWidget(listItem, itemWidget)

    def get_next_url(self):
        logger.debug("get_next_url")
        if self.queueList.count() > 0:
            item = self.queueList.takeItem(0)
            return item.urlResolved

    def highlight_next_item(self):
        logger.debug("highlight_next_item")
        if self.currentlyPlayingIndex >= 0:
            # Clear highlight of the previous item
            self.queueList.item(self.currentlyPlayingIndex).setBackground(Qt.white)

        self.currentlyPlayingIndex += 1

        if self.currentlyPlayingIndex < self.queueList.count():
            # Highlight the next item
            self.queueList.item(self.currentlyPlayingIndex).setBackground(Qt.lightGray)

    def reset_highlight(self):
        logger.debug("reset_highlight")
        if self.currentlyPlayingIndex >= 0:
            # Clear highlight of the current item
            self.queueList.item(self.currentlyPlayingIndex).setBackground(Qt.white)
        self.currentlyPlayingIndex = -1

    def clear(self):
        self.queueList.clear()
        self.currentlyPlayingIndex = -1

    def toggle_queue_visibility(self):
        logger.debug("toggle_queue_visibility")
        if self.queueList.isVisible():
            self.queueList.hide()
            self.toggleButton.setText(">")
        else:
            self.queueList.show()
            self.toggleButton.setText("<")

    def isEmpty(self):
        logger.debug("isEmpty")
        return self.queueList.count() == 0

    def get_current_url(self) -> UrlResolved:
        logger.debug(f"get_current_url - {self.currentlyPlayingIndex=}, {self.queueList.count()=}")
        if self.currentlyPlayingIndex == -1:
            self.currentlyPlayingIndex = 0
        if self.currentlyPlayingIndex < self.queueList.count():
            itemWidget = self.queueList.itemWidget(self.queueList.item(self.currentlyPlayingIndex))
            if isinstance(itemWidget, PlayerQueueItem):
                logger.debug(f"Current URL: {itemWidget.urlResolved.source_url}")
                return itemWidget.urlResolved
        return None
