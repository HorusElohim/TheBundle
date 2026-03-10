"""Buffered Opus audio source with jitter buffer for stable playback.

Discord.py's AudioPlayer loop calls ``source.read()`` every 20 ms and
sends the resulting frame over UDP.  When the source is an FFmpeg process
streaming from a remote URL, ``read()`` may block unpredictably due to
network latency or CDN throttling.  When a read stalls, the AudioPlayer
compensates by sending subsequent frames faster to "catch up", producing
audible speed-up / slow-down artefacts (see discord.py #9120).

This module solves the problem by inserting a **jitter buffer** between
FFmpeg and the AudioPlayer:

    [YouTube URL] ──▶ FFmpeg ──▶ _fill() thread ──▶ Queue ──▶ read() ──▶ AudioPlayer

- A background thread reads Opus frames from FFmpeg into a bounded queue
  as fast as FFmpeg produces them.
- ``read()`` pops from the queue, which is near-instant as long as the
  buffer has frames — so the AudioPlayer's 20 ms cadence is never disrupted.
- Before playback starts, ``make_source()`` blocks until the queue has
  pre-filled PREFILL_FRAMES (~1 s), eliminating the initial burst that
  causes the first-seconds speed-up.

FFmpeg flags
------------
before_options (input side):
    -reconnect / -reconnect_streamed / -reconnect_delay_max
        Auto-reconnect on transient HTTP failures.
    -analyzeduration 0 -probesize 32768
        Skip lengthy format probing — we already know it's audio.
    -thread_queue_size 4096
        Large input-thread packet queue inside FFmpeg itself.

options (output side):
    -vn                 Strip any video track.
    -b:a 256k           Opus bitrate (Discord supports up to 384 kbps).
    -bufsize 5M         Encoder rate-control buffer.
    -application audio  Use libopus MDCT mode optimised for music rather
                        than the default voice/low-delay mode.
"""

from __future__ import annotations

import queue
import threading

import discord

from bundle.core import logger

log = logger.get_logger(__name__)

FFMPEG_BEFORE_OPTIONS = (
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    " -analyzeduration 0 -probesize 32768"
    " -thread_queue_size 4096"
)
FFMPEG_OPTIONS = "-vn -b:a 256k -bufsize 5M -application audio"

# 500 frames × 20 ms = 10 seconds of pre-buffer
JITTER_BUFFER_SIZE = 250
# Pre-fill 250 frames (5 s) before playback begins
PREFILL_FRAMES = 250


class BufferedOpusAudio(discord.AudioSource):
    """Jitter buffer that decouples FFmpeg pipe reads from the 20 ms playback loop.

    Wraps any ``discord.FFmpegOpusAudio`` source with a bounded frame queue.
    A daemon thread (``_fill``) continuously reads Opus frames from FFmpeg and
    enqueues them.  The ``read()`` method — called by discord.py's AudioPlayer
    every 20 ms — simply dequeues the next frame, returning near-instantly
    regardless of upstream network conditions.

    Lifecycle::

        source = BufferedOpusAudio(ffmpeg_opus_source)
        source.wait_ready()   # block until PREFILL_FRAMES are buffered
        vc.play(source, ...)  # hand off to discord.py
        ...
        source.cleanup()      # signals the reader thread and cleans up FFmpeg

    Parameters
    ----------
    source:
        An already-constructed ``discord.FFmpegOpusAudio`` instance.
    """

    def __init__(self, source: discord.FFmpegOpusAudio) -> None:
        self._source = source
        self._buf: queue.Queue[bytes] = queue.Queue(maxsize=JITTER_BUFFER_SIZE)
        self._ended = threading.Event()
        self._ready = threading.Event()
        self._reader = threading.Thread(target=self._fill, daemon=True)
        self._reader.start()

    def _fill(self) -> None:
        """Background reader thread.

        Reads Opus frames from the underlying FFmpeg source and pushes them
        into ``_buf``.  The put uses short 250 ms timeouts so that the thread
        checks ``_ended`` frequently and can exit promptly when ``cleanup()``
        is called (e.g. on skip or stop).

        Sets ``_ready`` once PREFILL_FRAMES have been enqueued, unblocking
        any caller waiting in ``wait_ready()``.
        """
        try:
            frames = 0
            while not self._ended.is_set():
                data = self._source.read()
                if not data:
                    break
                # Retry put in short bursts so we notice _ended promptly
                while not self._ended.is_set():
                    try:
                        self._buf.put(data, timeout=0.25)
                        break
                    except queue.Full:
                        continue
                frames += 1
                if not self._ready.is_set() and frames >= PREFILL_FRAMES:
                    self._ready.set()
        except Exception as exc:
            log.debug("Jitter buffer reader stopped: %s", exc)
        finally:
            self._ready.set()
            self._ended.set()

    def wait_ready(self, timeout: float = 10.0) -> bool:
        """Block until the pre-fill target is reached. Returns True if ready."""
        return self._ready.wait(timeout=timeout)

    def read(self) -> bytes:
        """Return the next Opus frame from the buffer.

        Called by discord.py's AudioPlayer every ~20 ms.  Returns an empty
        ``bytes`` when the stream has ended and the buffer is drained, which
        signals the AudioPlayer to stop and fire the ``after`` callback.
        """
        if self._ended.is_set() and self._buf.empty():
            return b""
        try:
            return self._buf.get(timeout=0.5)
        except queue.Empty:
            return b""

    def is_opus(self) -> bool:
        """Tell discord.py that frames are already Opus-encoded."""
        return True

    def cleanup(self) -> None:
        """Signal the reader thread to stop and release FFmpeg resources."""
        self._ended.set()
        self._source.cleanup()


def make_source(stream_url: str) -> BufferedOpusAudio:
    """Create a buffered FFmpeg Opus source from a stream URL.

    Blocks until the jitter buffer has pre-filled (~1 s of audio)
    so playback starts smoothly without initial speed fluctuations.
    """
    raw = discord.FFmpegOpusAudio(
        stream_url,
        before_options=FFMPEG_BEFORE_OPTIONS,
        options=FFMPEG_OPTIONS,
    )
    source = BufferedOpusAudio(raw)
    source.wait_ready()
    return source
