import bundle
import signal


BIN_PATH = bundle.Path(r"C:\FFmpeg\ffmpeg-6.0-essentials_build\bin\ffmpeg.exe")


@bundle.data.dataclass
class FFmpegRecord(bundle.process.Process):
    bin_path: bundle.Path = bundle.data.field(default_factory=lambda: BIN_PATH)
    format: str = "gdigrab"
    framerate: float = 60
    width: int = 2560
    height: int = 1440
    input: str = "desktop"
    codec: str = "libx264"
    preset: str = "medium"
    pix_fmt: str = "yuv420p"
    output_file: str = "output.mp4"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    audio_channels: int = 2
    audio_sample_rate: int = 44100
    video_bitrate: str = "6000k"
    crf: int = 18  # Lower CRF value means better quality
    tune: str = "zerolatency"
    filters: str = ""
    profile: str = ""
    level: str = ""
    maxrate: str = ""
    bufsize: str = ""
    overwrite: bool = True
    duration: str = ""
    auto_save: bool = True

    def __post_init__(self):
        super().__post_init__()
        self.command = (
            f"{self.bin_path} "
            f"-f {self.format} "
            f"-framerate {self.framerate} "
            f"-video_size {self.width}x{self.height} "
            f"-i {self.input} "
            f"-c:v {self.codec} "
            f"-b:v {self.video_bitrate} "
            f"-crf {self.crf} "
            f"-preset {self.preset} "
            f"-pix_fmt {self.pix_fmt} "
            f"{f'-tune {self.tune} ' if self.tune else ''}"
            f"{f'-vf {self.filters} ' if self.filters else ''}"
            f"{f'-profile:v {self.profile} ' if self.profile else ''}"
            f"{f'-level {self.level} ' if self.level else ''}"
            f"{f'-maxrate {self.maxrate} ' if self.maxrate else ''}"
            f"{f'-bufsize {self.bufsize} ' if self.bufsize else ''}"
            f"-c:a {self.audio_codec} "
            f"-b:a {self.audio_bitrate} "
            f"-ac {self.audio_channels} "
            f"-ar {self.audio_sample_rate} "
            f"{'-y ' if self.overwrite else ''}"
            f"{f'-t {self.duration} ' if self.duration else ''}"
            f"{self.output_file}"
        )


if __name__ == "__main__":

    def signal_handler(sig, frame):
        print("Stopping recording...")
        ffrecord.terminate()

    signal.signal(signal.SIGINT, signal_handler)

    print("Starting recording. Press Ctrl+C to stop.")
    name = f"Recording_{bundle.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')}"
    ffrecord = FFmpegRecord(name=name)
    ffrecord()
