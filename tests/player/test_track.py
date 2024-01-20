import pytest
from bundle.player.track import TrackBase, TrackLocal
from bundle.player.medias import MP3
from PySide6.QtCore import QUrl
import bundle


def _load_image(path: bundle.Path):
    with open(path, "rb") as fd:
        return fd.read()


def test_mp3(assets_folder: bundle.Path, tmp_path: bundle.Path):
    # Load the MP3 file
    mp3_path = str(assets_folder / "file_example_MP3_700KB.mp3")
    mp3_instance = MP3.load(mp3_path)
    payload = open(mp3_instance.path, "rb").read()

    # Check initial state (you might need to adjust these assertions based on the actual initial state of your test MP3)
    assert mp3_instance.title == "Song"
    assert mp3_instance.artist == "Artist"
    assert mp3_instance.duration == 42
    # assert mp3_instance.thumbnail is not None

    # Modify the metadata and/or thumbnail
    mp3_instance.title = "New Test Title"
    mp3_instance.artist = "New Test Artist"
    mp3_instance.thumbnail = _load_image(bundle.player.config.ICON_PATH)
    mp3_instance.path = tmp_path / "modified_mp3.mp3"

    # Save the modified MP3 to a temporary location
    save_success = mp3_instance.save(payload)
    assert save_success

    # Reload the MP3 from the temporary location
    reloaded_mp3_instance = MP3.load(mp3_instance.path)

    # Verify that changes were saved correctly
    assert reloaded_mp3_instance.title == mp3_instance.title
    assert reloaded_mp3_instance.artist == mp3_instance.artist
    # To do - rewrite sample test to contain fixed thumbnail
    # assert reloaded_mp3_instance.thumbnail == mp3_instance.thumbnail


def test_track_local_parse_metadata(assets_folder):
    mp3_path = str(assets_folder / "file_example_MP3_700KB.mp3")
    track_local = TrackLocal(path=QUrl(f"file:///{mp3_path}"))
    assert track_local.track.is_valid()
    assert track_local.track.title == "Song"
    assert track_local.track.artist == "Artist"
    assert track_local.track.duration == 42
    assert track_local.duration_str == "00:00:42"
