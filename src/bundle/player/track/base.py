from __future__ import annotations

import bundle
from ..medias import MP3, MP4


@bundle.Data.dataclass
class TrackBase(bundle.Entity):
    track: MP3 | MP4 | None = None

    @property
    def duration_str(self) -> str:
        mins, secs = divmod(self.track.duration, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def is_valid(self):
        return self.track.is_valid() if self.track else False
