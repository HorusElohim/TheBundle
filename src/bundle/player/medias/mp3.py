import bundle
import hashlib
from mutagen.mp3 import MP3 as MutagenMP3
from mutagen.id3 import ID3, APIC, error, TIT2, TPE1

from . import sanitize_pathname
from ..config import DATA_PATH

MP3_PATH = DATA_PATH / "mp3"
MP3_PATH.mkdir(exist_ok=True, parents=True)

logger = bundle.getLogger(__name__)


@bundle.Data.dataclass
class MP3(bundle.Entity):
    title: str = bundle.Data.field(default_factory=str)
    duration: int = bundle.Data.field(default_factory=int)
    artist: str = bundle.Data.field(default_factory=str)
    thumbnail: bytes = bundle.Data.field(default_factory=bytes, repr=False)
    path: str | bundle.Path = "auto"

    @property
    def identifier(self) -> str:
        data_to_hash = (self.title + self.artist).encode("utf-8")
        hash_object = hashlib.sha256(data_to_hash)
        return hash_object.hexdigest()

    def is_valid(self):
        return self.title and self.duration and self.artist and self.thumbnail

    @classmethod
    def load(cls, path: str | bundle.Path) -> "MP3":
        """Load MP3 metadata from a file."""
        logger.debug(f"loading mp3 from: {path}")
        audio = MutagenMP3(path, ID3=ID3)

        # Extract metadata
        title = audio.get("TIT2", [None])[0]
        artist = audio.get("TPE1", [None])[0]
        duration = int(audio.info.length)

        # Extract thumbnail
        thumbnail_data = None
        if "APIC:Cover" in audio.tags:
            thumbnail_data = audio.tags["APIC:Cover"].data
            logger.debug(f"loading thumbnail: {len(thumbnail_data)}")

        return cls(
            title=title,
            artist=artist,
            duration=duration,
            thumbnail=thumbnail_data,
            path=path,
        )

    def save(self, payload: bytes | None = None, only_metadata: bool = False) -> bool:
        """Save the instance's data back to the MP3 file."""
        status = True
        try:
            if not only_metadata:
                if payload is None:
                    raise ValueError("Missing payload to save")

                if self.path == "auto":
                    self.path = MP3_PATH / f"{self.title}-{self.artist}.mp3"
                    self.path = sanitize_pathname(self.path)

                with open(self.path, "wb") as fd:
                    fd.write(payload)

            if not bundle.Path(self.path).exists():
                raise ValueError(f"FileNotExist: {self.path}")

            audio = MutagenMP3(self.path, ID3=ID3)

            # Add ID3 tag if it doesn't exist
            try:
                audio.add_tags()
            except error:
                pass

            # Set metadata
            audio.tags.add(TIT2(encoding=3, text=self.title))
            audio.tags.add(TPE1(encoding=3, text=self.artist))

            # Set thumbnail
            if len(self.thumbnail) > 0:
                logger.debug(f"adding thumbnail")
                audio.tags.add(APIC(encoding=3, mime="image/png", type=3, desc="Cover", data=self.thumbnail))

            audio.save()
        except Exception as e:
            logger.error(f"Error saving MP3 metadata: {e}")
            status = False
        finally:
            logger.debug(f"{bundle.core.Emoji.status(status)}")
            return status
