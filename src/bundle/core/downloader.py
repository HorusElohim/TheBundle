# Copyright 2024 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import asyncio
from pathlib import Path

import aiohttp
from aiofiles import open as aio_open
from tqdm.asyncio import tqdm_asyncio

from ..core import logger, tracer

log = logger.get_logger(__name__)


class Downloader:
    """
    Handles asynchronous downloading of files from a specified URL.

    Attributes:
        url (str): The URL to download the file from.
        destination (Path | None): The local file path to save the downloaded file. If None, data is stored in memory.
        chunk_size (int): The size of each chunk to download at a time.
        buffer (bytearray): A buffer to temporarily store the file's content if no destination is specified.

    Methods:
        start(byte_size: int): Placeholder for initialization logic before downloading starts.
        update(byte_count: int): Placeholder for update logic as chunks of data are downloaded.
        end(): Placeholder for cleanup logic after the download completes.
        download() -> bool: Asynchronously downloads a file from `url` to `destination` or to `buffer`.
    """

    def __init__(
        self,
        url: str,
        destination: Path | None = None,
        chunk_size: int = 4096,
    ):
        self.url = url
        self.destination = destination
        self.chunk_size = chunk_size
        self.buffer = bytearray()

    def start(self, byte_size: int):
        """Initializes the download process. Placeholder for subclasses to implement."""
        pass

    def update(self, byte_count: int):
        """Updates the download progress. Placeholder for subclasses to implement."""
        pass

    def end(self):
        """Finalizes the download process. Placeholder for subclasses to implement."""
        pass

    async def download(self) -> bool:
        """
        Asynchronously downloads a file from the specified URL.

        The file is either saved to the given destination path or stored in an in-memory buffer.
        Utilizes aiohttp for asynchronous HTTP requests and aiofiles for async file I/O operations.

        Returns:
            bool: True if the download was successful, False otherwise.
        """
        status = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as response:
                    if response.status != 200:
                        log.error(f"Error downloading {self.url}. Status: {response.status}")
                        return False

                    byte_size = int(response.headers.get("content-length", 0))
                    await tracer.Async.call_raise(self.start, byte_size)

                    if self.destination:
                        self.destination.parent.mkdir(parents=True, exist_ok=True)
                        async with aio_open(self.destination, "wb") as fd:
                            async for chunk in response.content.iter_chunked(self.chunk_size):
                                await tracer.Async.call_raise(fd.write, chunk, log_level=logger.Level.VERBOSE)
                                await tracer.Async.call_raise(self.update, len(chunk), log_level=logger.Level.VERBOSE)
                                await asyncio.sleep(0)
                    else:
                        async for chunk in response.content.iter_chunked(self.chunk_size):
                            self.buffer.extend(chunk)
                            await tracer.Async.call_raise(self.update, len(chunk))
                            await asyncio.sleep(0)
                    status = True

        except Exception as ex:
            log.error(f"Error downloading {self.url}. Exception: {ex}")
        finally:
            await tracer.Async.call_raise(self.end)
            log.debug("%s", logger.Emoji.status(status))
            return status


class DownloaderTQDM(Downloader):
    """
    Extends Downloader with TQDM progress bar for visual feedback during download.

    Overrides the start, update, and end methods of Downloader to integrate a TQDM
    progress bar that updates with each downloaded chunk.
    """

    def start(self, byte_size: int):
        """Initializes the TQDM progress bar."""
        self.progress_bar = tqdm_asyncio(
            total=byte_size,
            desc=f"Downloading {self.destination.name if self.destination else 'file'}",
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        )

    def update(self, byte_count: int):
        """Updates the TQDM progress bar with the number of bytes downloaded."""
        if hasattr(self, "progress_bar"):
            self.progress_bar.update(byte_count)

    def end(self):
        """Closes the TQDM progress bar."""
        if hasattr(self, "progress_bar"):
            self.progress_bar.close()
