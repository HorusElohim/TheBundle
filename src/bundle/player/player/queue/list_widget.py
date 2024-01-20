from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

import bundle

logger = bundle.getLogger(__name__)


class ListWidget(QListWidget):
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
