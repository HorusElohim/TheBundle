import asyncio
import time
from pathlib import Path
from random import randint

import rich_click as click

from bundle.core import logger, tracer
from bundle.youtube import media, pytube
from bundle.youtube.database import Database

from . import YOUTUBE_PATH

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def youtube():
    import nest_asyncio

    nest_asyncio.apply()


@youtube.command("new-token")
@tracer.Sync.decorator.call_raise
async def new_token():
    log.info(f"generating poto token")
    await pytube.generate_token()


@youtube.command()
@click.argument("url", type=str)
@click.option("directory", "-d", type=click.Path(exists=True), default=YOUTUBE_PATH, help="Destination Folder")
@click.option("--dry-run", "-dr", is_flag=True, help="Dry run, without any download just resolve the URL")
@click.option("--mp3", is_flag=True, help="Download MP4 and convert to MP3")
@click.option("--mp3-only", is_flag=True, help="Download MP4 and convert to MP3")
@tracer.Sync.decorator.call_raise
async def download(url, directory, dry_run, mp3, mp3_only):
    log.info(f"started {url=}")
    directory = Path(directory)
    db = Database(path=directory)
    await db.load()
    semaphore = asyncio.Semaphore(1)

    async for youtube_track in pytube.resolve(url):
        if not youtube_track.is_resolved():
            log.error("Unable to resolve metadata for %s", url)
            continue
        # Check in Database
        if db.has(youtube_track.identifier):
            log.info(f"✨ Already present - {youtube_track.filename}")
            return 0
        # Dry run
        if dry_run:
            log.info(f"YoutubeTrack:\n{await youtube_track.as_json()}")
            return 0
        # Download MP4
        mp4 = await media.MP4.download(youtube_track, directory)
        db.add(mp4)
        # In Mp3
        if mp3 or mp3_only:
            _mp3 = await mp4.extract_mp3()
            db.add(_mp3)
            if mp3_only:
                mp4.path.unlink()
        # Safe sleep (avoid been blocked)
        if await pytube.is_playlist(url) and not dry_run:
            sleep_time = 2 + randint(10, 5200) / 1000
            log.info(f"sleeping {sleep_time:.2f} seconds")
            time.sleep(sleep_time)


@youtube.command()
@click.argument("url", type=str)
@click.option("--limit", type=int, default=0, show_default=False, help="Limit how many entries to display")
@tracer.Sync.decorator.call_raise
async def resolve(url, limit):
    """Resolve a YouTube URL and log the resulting track metadata."""
    log.info("Resolving %s", url)
    count = 0
    async for youtube_track in pytube.resolve(url):
        if not youtube_track.is_resolved():
            log.error("Resolver returned an empty track for %s", url)
            continue
        log.info(await youtube_track.as_json())
        count += 1
        if limit and count >= limit:
            break
    if count == 0:
        log.warning("No track metadata resolved for %s", url)
    else:
        log.info("Resolved %d entr%s", count, "y" if count == 1 else "ies")


@click.group()
@tracer.Sync.decorator.call_raise
async def track():
    pass


@track.command()
@click.argument("track_path", type=click.Path(exists=True))
@tracer.Sync.decorator.call_raise
async def info(track_path: Path):
    track = None
    track_path = Path(track_path)
    if track_path.suffix == ".mp4":
        track = await media.MP4.load(track_path)
    elif track_path.suffix == ".mp3":
        track = await media.MP3.load(track_path)
    if track:
        log.info(await track.as_json())
        thumbnail = await track.get_thumbnail()
        log.info(f"thumbnail - len:{len(thumbnail) if thumbnail else 0}")


@track.command()
@click.argument("track_paths", nargs=-1, type=click.Path(exists=True))
@tracer.Sync.decorator.call_raise
async def to_mp3(track_paths):

    @tracer.Async.decorator.call_raise
    async def extract_mp4_audio(track_path: Path):
        if not track_path.suffix == ".mp4":
            log.warning(f"Only MP4 audio extraction to MP3 is supported. Skipping: {track_path}")
            return

        log.info(f"🎶 Audio extraction started on: {track_path}")
        mp4 = await media.MP4.load(track_path)
        mp3 = await mp4.extract_mp3()
        del mp3, mp4

    tasks = [extract_mp4_audio(Path(track_path)) for track_path in track_paths]
    await asyncio.gather(*tasks)


@click.group()
@tracer.Sync.decorator.call_raise
async def database():
    pass


@database.command()
@click.option("-d", "directory", type=click.Path(exists=True), default=YOUTUBE_PATH, help="Destination directory")
@tracer.Sync.decorator.call_raise
async def show(directory):
    db = Database(path=directory)
    await db.load()
    log.info(await db.as_json())


youtube.add_command(track)
youtube.add_command(database)

if __name__ == "__main__":
    youtube()
