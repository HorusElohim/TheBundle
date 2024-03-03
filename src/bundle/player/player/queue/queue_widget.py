from threading import Lock
from PySide6.QtWidgets import QListWidgetItem, QVBoxLayout, QWidget
from bundle import logger
import random

from .list_widget import ListWidget
from .item_widget import QueueItemWidget
from ...track import TrackBase

log = logger.getLogger(__name__)


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
        log.debug("isEmpty")
        return self.queueList.count() == 0

    def get_current_track(self) -> TrackBase | None:
        if 0 <= self.current_index < self.queueList.count():
            itemWidget = self.queueList.itemWidget(self.queueList.item(self.current_index))
            if isinstance(itemWidget, QueueItemWidget):
                log.debug(f"returning current track: {itemWidget.track.track.path}")
                return itemWidget.track
        log.debug(f"no current track")
        return None

    def get_current_track_index(self) -> int:
        return self.current_index

    def _create_list_item_widget(self, track: TrackBase) -> tuple[QueueItemWidget, QListWidgetItem]:
        item_widget = QueueItemWidget(self, track)
        list_item = QListWidgetItem(self.queueList)
        list_item.setSizeHint(item_widget.sizeHint())
        log.debug(f"{logger.Emoji.success}")
        return item_widget, list_item

    def add_track(self, track: TrackBase):
        if track is not None and track.track is not None:
            queue_item, list_item = self._create_list_item_widget(track)
            self.queueList.addItem(list_item)
            self.queueList.setItemWidget(list_item, queue_item)
            if self.queueList.count() == 1:
                self.select_track(0)
            log.debug(f"{logger.Emoji.success}")
        else:
            log.warning(f"track {track}")

    def has_next(self) -> int:
        has_next = self.current_index < self.queueList.count() - 1
        log.debug(f"has_next: {has_next}")
        return has_next

    def next_track(self):
        if self.queueList.count() > 0 and self.current_index < self.queueList.count() - 1:
            log.debug(f"next_track from: {self.current_index}")
            self.select_track(self.current_index + 1)
            log.debug(f"next_track to: {self.current_index}")
        else:
            log.warning("no next_track")

    def previous_track(self):
        if self.current_index >= 1:
            log.debug(f"previous_track from: {self.current_index}")
            self.select_track(self.current_index - 1)
            log.debug(f"previous_track to: {self.current_index}")
            log.debug("previous_track")
            return
        log.debug("no previous_track")

    def remove_track(self, index: int):
        log.debug(f"remove_track: {index}")
        if 0 <= index < self.queueList.count():
            self.queueList.takeItem(index)
            if self.current_index >= index:
                self.current_index -= 1

    def select_track(self, index: int):
        log.debug(f"select_track: {index}")
        self.reset_selection()
        if 0 <= index < self.queueList.count():
            self.current_index = index
            item_widget = self.queueList.itemWidget(self.queueList.item(index))
            if isinstance(item_widget, QueueItemWidget):
                item_widget.setSelectedStyle()

    def reset_selection(self):
        for i in range(self.queueList.count()):
            item_widget = self.queueList.itemWidget(self.queueList.item(i))
            if isinstance(item_widget, QueueItemWidget):
                item_widget.resetStyle()

    def shuffle_tracks(self):
        count = self.queueList.count()
        log.debug(f"shuffling tracks: {count}")
        if count <= 1:
            return  # No need to shuffle if 0 or 1 item
        tracks = []
        for i in range(count):
            item_widget = self.queueList.itemWidget(self.queueList.item(i))
            if isinstance(item_widget, QueueItemWidget):
                tracks.append(item_widget.track)
        random.shuffle(tracks)
        self.queueList.clear()
        for track in tracks:
            self.add_track(track)

        self.select_track(0)
