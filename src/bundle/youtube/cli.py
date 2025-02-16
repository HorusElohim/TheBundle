import asyncio
import time
from pathlib import Path
from random import randint

import asyncclick as click

from bundle.youtube import LOGGER
from bundle.youtube.database import Database
from bundle.youtube.media import MP3, MP4
from bundle.youtube.resolver import resolve

from . import YOUTUBE_PATH
from ..core.downloader import Downloader, DownloaderTQDM


@click.group()
def main():
    pass


@main.command()
@click.argument("url", type=str)
@click.option("directory", "-d", type=click.Path(exists=True), default=YOUTUBE_PATH, help="Destination Folder")
@click.option("--dry-run", "-dr", is_flag=True, help="Dry run, without any download just resolve the URL")
@click.option("--mp3", is_flag=True, help="Download MP4 and convert to MP3")
@click.option("--mp3-only", is_flag=True, help="Download MP4 and convert to MP3")
async def download(url, directory, dry_run, mp3, mp3_only):
    LOGGER.info(f"started {url=}")
    directory = Path(directory)
    db = Database(path=directory)
    await db.load()

    semaphore = asyncio.Semaphore(1)

    async for youtube_track in resolve(url):
        sleep_time = 2 + randint(10, 5200) / 1000
        LOGGER.info(f"sleeping {sleep_time:.2f} seconds")
        if not dry_run:
            time.sleep(sleep_time)

        if await db.has(youtube_track.identifier):
            LOGGER.info(f"✨ Already present - {youtube_track.filename}")
            continue
        if dry_run:
            LOGGER.info(f"YoutubeTrack:\n{await youtube_track.as_json()}")
            continue
        LOGGER.info(f"🎶 - {youtube_track.filename}")
        target_path = directory / f"{youtube_track.filename}.mp4"
        audio_downloader = DownloaderTQDM(url=youtube_track.video_url, destination=target_path)
        thumbnail_downloader = Downloader(url=youtube_track.thumbnail_url)

        async with semaphore:
            await asyncio.gather(audio_downloader.download(), thumbnail_downloader.download())

        mp4 = MP4.from_track(path=target_path, track=youtube_track)
        await mp4.save(thumbnail_downloader.buffer)
        if mp3 or mp3_only:
            # takes some times then no need to sleep afterwards (required to not be blocked)
            as_mp3 = await mp4.as_mp3()
            await db.add(mp4)
            if mp3_only:
                mp4.path.unlink()
            await db.add(as_mp3)
        else:
            await db.add(mp4)


@click.group()
def track():
    pass


@track.command()
@click.argument("track_path", type=click.Path(exists=True))
async def info(track_path: Path):
    track = None
    track_path = Path(track_path)
    if track_path.suffix == ".mp4":
        track = await MP4.load(track_path)
    elif track_path.suffix == ".mp3":
        track = await MP3.load(track_path)
    if track:
        LOGGER.info(await track.as_json())
        thumbnail = await track.get_thumbnail()
        LOGGER.info(f"thumbnail - len:{len(thumbnail) if thumbnail else 0}")


@track.command()
@click.argument("track_paths", nargs=-1, type=click.Path(exists=True))
async def extract_audio(track_paths):
    async def extract_mp4_audio(track_path: Path):
        track_path = Path(track_path)
        if not track_path.suffix == ".mp4":
            LOGGER.warning(f"Only MP4 audio extraction to MP3 is supported. Skipping: {track_path}")
            return
        try:
            LOGGER.info(f"🎶 Audio extraction started on: {track_path}")
            mp4 = await MP4.load(track_path)
            if mp4:
                mp3 = await mp4.as_mp3()
                LOGGER.info(f"✨ Audio extraction completed: {mp3.filename}")
                del mp3
                del mp4
            else:
                LOGGER.error(f"Failed to load MP4: {track_path}")
        except Exception as e:
            LOGGER.error(f"Error processing {track_path}: {e}")

    tasks = [extract_mp4_audio(track_path) for track_path in track_paths]
    await asyncio.gather(*tasks)


@click.group()
def database():
    pass


@database.command()
@click.option("-d", "directory", type=click.Path(exists=True), default=YOUTUBE_PATH, help="Destination directory")
async def show(directory):
    db = Database(path=directory)
    await db.load()
    LOGGER.info(await db.as_json())


main.add_command(track)
main.add_command(database)

if __name__ == "__main__":
    main()
