from pynput import keyboard
from PySide6.QtGui import QIcon
from PySide6.QtCore import QObject, QSize, Qt, QUrl
from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow
from pathlib import Path
from .player import Player, popup
from . import track
from . import config
from . import medias
from logging import getLogger

logger = getLogger(__name__)


def resolve_url(url: str | QUrl) -> track.TrackBase | None:
    logger.debug("resolving: %s", url)
    match url:
        case str():
            if "youtu" in url:
                if "playlist" in url:
                    popup.critical_popup(
                        None,
                        "Detected Youtube Playlist",
                        "Please avoid youtube urls has 'https://music.youtube.com/playlist?list=' ",
                    )
                    return None
                return track.TrackYoutube(url=url)
            else:
                raise ValueError(f"No yet implemented: {url=}")
        case QUrl():
            return track.TrackLocal(path=url)


class MediaKeyHandler(QObject):
    play_pause_signal = Signal()
    next_track_signal = Signal()
    previous_track_signal = Signal()

    def __init__(self):
        super().__init__()
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()

    def on_press(self, key):
        try:
            if key == keyboard.Key.media_play_pause:
                self.play_pause_signal.emit()
            elif key == keyboard.Key.media_next:
                self.next_track_signal.emit()
            elif key == keyboard.Key.media_previous:
                self.previous_track_signal.emit()
        except AttributeError:
            pass


class TrackLoaderThread(QThread):
    track_found = Signal(track.TrackLocal)  # Signal to emit when a track is found
    finished = Signal()  # Signal to indicate job completion

    def run(self):
        logger.debug("Loading tracks in TrackLoaderThread")
        for track_path in medias.MP4_PATH.iterdir():
            if track_path.suffix == ".mp4":
                logger.debug(f"Found track: {track_path}")
                local_track = track.TrackLocal(path=track_path)
                self.track_found.emit(local_track)

        self.finished.emit()


class ThreadURLResolver(QThread):
    track_resolved = Signal(track.TrackBase)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        resolved_track = resolve_url(self.url)
        if resolved_track:
            self.track_resolved.emit(resolved_track)


class BundlePlayerWindows(QMainWindow):
    def __init__(self):
        super().__init__()
        self.player = Player()
        self.setCentralWidget(self.player)
        self.setWindowTitle("BundlePlayer")
        self.setContentsMargins(0, 0, 0, 0)
        self.setWindowTitle(config.APP_NAME)
        self.setGeometry(800, 180, 666, 666)
        self.resize(QSize(800, 666))
        self.setWindowIcon(QIcon(str(config.ICON_PATH.absolute())))
        self.resize(800, 600)
        self.setAcceptDrops(True)
        # Threads URL resolvers
        self._threads = []
        # Handle keyboard special play/pause next/back
        self._create_and_start_mediakey_handler()
        # Load saved tracks
        self._create_and_start_loading_thread()

    def _create_and_start_mediakey_handler(self):
        self.media_handler = MediaKeyHandler()
        # Connect signals to your player's methods
        self.media_handler.play_pause_signal.connect(self.player.toggle_play_pause)
        self.media_handler.next_track_signal.connect(self.player.play_next_track)
        self.media_handler.previous_track_signal.connect(self.player.play_previous_track)

    def _create_and_start_loading_thread(self):
        self.track_loader_thread = TrackLoaderThread()
        self.track_loader_thread.track_found.connect(self.add_track_slot)
        self.track_loader_thread.finished.connect(self.track_loader_thread.quit)
        self.track_loader_thread.finished.connect(self.track_loader_thread.deleteLater)
        self.track_loader_thread.start()
        logger.debug("loading thread started")

    def _create_and_start_url_resolver_thread(self, url: str | QUrl):
        logger.debug("add_track_from_url")
        thread = ThreadURLResolver(url)
        thread.track_resolved.connect(self.add_track_slot)
        thread.finished.connect(lambda: self.cleanup_thread(thread))
        thread.start()
        logger.debug("url resolver thread started")
        self._threads.append(thread)

    def dropEvent(self, event):
        logger.debug("drop")
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            url = mimeData.urls()[0]
            self.add_track_from_url(url)
        else:
            logger.error(f"drop has no url: {mimeData}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_V and (event.modifiers() & Qt.ControlModifier):
            logger.debug("paste")
            clipboard = QApplication.clipboard()
            clipboard_url = clipboard.text()
            if clipboard_url:
                self.add_track_from_url(clipboard_url)

    def add_track_from_url(self, url: str | QUrl):
        logger.debug("add_track_from_url")
        self._create_and_start_url_resolver_thread(url)

    @Slot(track.TrackBase)
    def add_track_slot(self, track_base: track.TrackBase):
        logger.debug(f"Adding track type <{track_base.class_type}>: {track_base.path}")
        self.player.add_track(track_base)

    def cleanup_thread(self, thread):
        logger.debug(f"cleaning up thread: {thread}")
        thread.deleteLater()
        self._threads.remove(thread)


def main():
    app = QApplication([])
    app.setStyle("fusion")

    # Create and show the main window
    main_window = BundlePlayerWindows()
    main_window.show()

    app.exec()


if __name__ == "__main__":
    main()
