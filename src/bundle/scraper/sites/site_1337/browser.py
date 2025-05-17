from __future__ import annotations

import asyncio

from tabulate import tabulate

from ....core import browser, logger
from .data import TorrentData

log = logger.get_logger(__name__)


class Browser(browser.Browser):
    """
    A specialized browser class for parsing 1337x.to search results,
    including extracting magnet links from detail pages.
    """

    url_suffix: str = "https://1337x.to/"

    async def set_context(self) -> Browser:
        return await self.new_context(
            user_agent=("Mozilla/5.0 (X11; Linux x86_64; rv:101.0) " "Gecko/20100101 Firefox/101.0"),
            locale="en-US",
        )

    async def get_search_url(self, name: str, page: int = 1) -> str:
        return f"{self.url_suffix}search/{'+'.join(name.split())}/{page}/"

    async def get_torrents(self, page: browser.Page) -> list[TorrentData]:
        log.debug("Begin parsing torrents from page...")

        table = self.Table(
            row_selector="table.table-list tbody tr",
            columns=[
                self.Table.Column(
                    name="name", selector="td.coll-1.name a:nth-of-type(2)", parser_type=self.Table.Column.Type.TEXT
                ),
                self.Table.Column(
                    name="detail_url",
                    selector="td.coll-1.name a:nth-of-type(2)",
                    parser_type=self.Table.Column.Type.URL,
                    base_url=self.url_suffix,
                ),
                self.Table.Column(name="seeds", selector="td.coll-2.seeds", parser_type=self.Table.Column.Type.INT),
                self.Table.Column(name="leeches", selector="td.coll-3.leeches", parser_type=self.Table.Column.Type.INT),
                self.Table.Column(name="uploaded_at", selector="td.coll-date", parser_type=self.Table.Column.Type.TEXT),
                self.Table.Column(name="size", selector="td.coll-4", parser_type=self.Table.Column.Type.TEXT),
                self.Table.Column(name="uploader", selector="td.coll-5 a", parser_type=self.Table.Column.Type.TEXT),
            ],
            model=TorrentData,
        )

        torrents = await self.extract_table(page, table)
        # initialize magnet_link so field exists
        for t in torrents:
            t.magnet_link = ""

        if torrents:
            await asyncio.gather(*(self._fetch_magnet_link_for_torrent(t) for t in torrents if t.detail_url))

        log.debug("Total parsed torrents with magnet links: %d", len(torrents))
        return torrents

    async def _fetch_magnet_link_for_torrent(self, torrent: TorrentData) -> None:
        log.debug("Fetching magnet link for %r", torrent.name)
        page = await self.new_page()
        await page.goto(torrent.detail_url, wait_until="commit")
        await page.wait_for_selector("a#openPopup")
        torrent.magnet_link = (await page.get_attribute("a#openPopup", "href")) or ""
        await page.close()

    async def tabulate_torrents(self, torrents: list[TorrentData], truncate_width: int = 30) -> str:
        def _truncate(text: str) -> str:
            return text if len(text) <= truncate_width else text[: truncate_width - 3] + "..."

        table_data = [
            [
                idx + 1,
                t.name,
                t.seeds,
                t.leeches,
                t.uploaded_at,
                t.size,
                _truncate(t.uploader),
            ]
            for idx, t in enumerate(torrents)
        ]
        headers = [
            "#",
            "Name",
            "Seeds",
            "Leeches",
            "Uploaded At",
            "Size",
            "Uploader",
        ]
        grid = tabulate(table_data, headers=headers, tablefmt="fancy_grid")

        links = "\n\n".join(
            f"[{i+1}] Detail URL: {t.detail_url}\n    Magnet Link: {t.magnet_link}" for i, t in enumerate(torrents)
        )

        return f"\n{grid}\n\nLinks:\n{links}"
