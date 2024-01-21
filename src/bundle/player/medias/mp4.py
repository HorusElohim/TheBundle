import bundle
import ffmpeg

from .mp3 import MP3, MP3_PATH
from ..config import DATA_PATH

MP4_PATH = DATA_PATH / "mp4"
MP4_PATH.mkdir(exist_ok=True, parents=True)

logger = bundle.getLogger(__name__)


@bundle.Data.dataclass
class MP4(bundle.Data.Json):
    title: str = bundle.Data.field(default_factory=str)
    duration: int = bundle.Data.field(default_factory=int)
    artist: str = bundle.Data.field(default_factory=str)
    thumbnail: bytes = bundle.Data.field(default_factory=bytes, repr=False)
    path: str | bundle.Path = "auto"

    def is_valid(self):
        return self.title and self.duration and self.artist and self.thumbnail

    @classmethod
    def load(cls, path: str | bundle.Path) -> "MP4":
        """Load MP4 metadata from a file."""
        # FIXME
        # Add properly metadata in MP4
        mp3_path = MP3_PATH / path.name.replace(".mp4", ".mp3")
        if mp3_path.exists():
            mp3 = MP3.load(mp3_path)
        else:
            raise NotImplemented("MP4 metadata is not yet implemented")
        return cls(
            title=mp3.title,
            artist=mp3.artist,
            duration=mp3.duration,
            thumbnail=mp3.thumbnail,
            path=path,
        )

    def save(self, data: bytes | None = None, only_metadata: bool = False) -> bool:
        """Save the instance's data back to the MP4 file."""
        status = True
        try:
            if not only_metadata:
                if data is None:
                    raise ValueError("Missing data to save")

                if self.path == "auto":
                    # Define how to automatically set the file path
                    self.path = MP4_PATH / f"{self.title}-{self.artist}.mp4"
                    logger.debug(f"auto-name: {self.path}")

                with open(self.path, "wb") as fd:
                    fd.write(data)
                logger.debug(f"data saved: {len(data) / 1024 / 1024} Mb")
        except Exception as e:
            logger.error(f"Error saving MP4 metadata: {e}")
            status = False
        finally:
            logger.debug(f"{bundle.core.Emoji.success if status else bundle.core.Emoji.failed}")
            return status

    def as_mp3(self) -> MP3:
        """Extract the MP4 file to an MP3 file."""
        try:
            logger.debug("start extracting mp3")
            output_path = MP3_PATH / f"{self.title}-{self.artist}.mp3"
            # Extract audio stream and save as MP3
            (
                ffmpeg.input(str(self.path))
                .output(str(output_path), format="mp3", acodec="libmp3lame", **{"qscale:a": 1}, loglevel="quiet")
                .run(overwrite_output=True)
            )
            logger.info(f"Extraction MP4 to MP3: {output_path}")
            logger.debug("ffmpeg extraction completed")
            mp3 = MP3(title=self.title, artist=self.artist, thumbnail=self.thumbnail, path=output_path)
            mp3.save(only_metadata=True)
            return MP3.load(output_path)
        except ffmpeg.Error as e:
            logger.error(f"Error in extracting MP4 to MP3: {e}")
            raise
