from threading import Lock
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidgetItem, QVBoxLayout, QWidget
from typing import Tuple
import bundle
import random

from .list_widget import ListWidget
from .item_widget import QueueItemWidget
from ...track import TrackBase

logger = bundle.getLogger(__name__)


class PlayerQueue(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(55)
        self.setStyleSheet("background-color: black;")
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 5, 0)
        self.setLayout(self.mainLayout)
        self.queueList = ListWidget()
        self.mainLayout.addWidget(self.queueList)
        self._current_index = -1
        self._index_lock = Lock()

    @property
    def current_index(self) -> int:
        with self._index_lock:
            return self._current_index

    @current_index.setter
    def current_index(self, index: int):
        with self._index_lock:
            self._current_index = index

    def clear(self):
        self.queueList.clear()
        self.current_index = -1

    def isEmpty(self):
        logger.debug("isEmpty")
        return self.queueList.count() == 0

    def get_current_track(self) -> TrackBase | None:
        if 0 <= self.current_index < self.queueList.count():
            itemWidget = self.queueList.itemWidget(self.queueList.item(self.current_index))
            if isinstance(itemWidget, QueueItemWidget):
                logger.debug(f"returning current track: {itemWidget.track.track.path}")
                return itemWidget.track
        logger.debug(f"no current track")
        return None

    def get_current_track_index(self) -> int:
        return self.current_index

    def _create_list_item_widget(self, track: TrackBase) -> tuple[QueueItemWidget, QListWidgetItem]:
        item_widget = QueueItemWidget(self, track)
        list_item = QListWidgetItem(self.queueList)
        list_item.setSizeHint(item_widget.sizeHint())
        logger.debug("list item widget created")
        logger.debug(f"{bundle.core.Emoji.success}")
        return item_widget, list_item

    def add_track(self, track: TrackBase):
        queue_item, list_item = self._create_list_item_widget(track)
        self.queueList.addItem(list_item)
        self.queueList.setItemWidget(list_item, queue_item)
        if self.queueList.count() == 1:
            self.select_track(0)
        logger.debug(f"{bundle.core.Emoji.success}")

    def has_next(self) -> int:
        has_next = self.current_index < self.queueList.count() - 1
        logger.debug(f"has_next: {has_next}")
        return has_next

    def next_track(self):
        if self.queueList.count() > 0 and self.current_index < self.queueList.count() - 1:
            logger.debug(f"next_track from: {self.current_index}")
            self.select_track(self.current_index + 1)
            logger.debug(f"next_track to: {self.current_index}")
        else:
            logger.warning("no next_track")

    def previous_track(self):
        if self.current_index >= 1:
            logger.debug(f"previous_track from: {self.current_index}")
            self.select_track(self.current_index - 1)
            logger.debug(f"previous_track to: {self.current_index}")
            logger.debug("previous_track")
            return
        logger.debug("no previous_track")

    def remove_track(self, index: int):
        logger.debug(f"remove_track: {index}")
        if 0 <= index < self.queueList.count():
            self.queueList.takeItem(index)
            if self.current_index >= index:
                self.current_index -= 1

    def select_track(self, index: int):
        logger.debug(f"select_track: {index}")
        self.reset_selection()  # Reset selection for all items first
        if 0 <= index < self.queueList.count():
            self.current_index = index
            item_widget = self.queueList.itemWidget(self.queueList.item(index))
            if isinstance(item_widget, QueueItemWidget):
                # Set the style for the selected widget
                item_widget.setSelectedStyle()  # Implement this method in QueueItemWidget

    def reset_selection(self):
        for i in range(self.queueList.count()):
            item_widget = self.queueList.itemWidget(self.queueList.item(i))
            if isinstance(item_widget, QueueItemWidget):
                # Reset the style for each widget
                item_widget.resetStyle()  # Implement this method in QueueItemWidget

    def shuffle_tracks(self):
        count = self.queueList.count()
        logger.debug(f"shuffling tracks: {count}")
        if count <= 1:
            return  # No need to shuffle if 0 or 1 item

        # Extract track information
        tracks = []
        for i in range(count):
            item_widget = self.queueList.itemWidget(self.queueList.item(i))
            if isinstance(item_widget, QueueItemWidget):
                tracks.append(item_widget.track)

        # Shuffle the tracks
        random.shuffle(tracks)

        # Clear the QListWidget and repopulate
        self.queueList.clear()
        for track in tracks:
            self.add_track(track)  # Reuse your existing method to add tracks

        self.select_track(0)
