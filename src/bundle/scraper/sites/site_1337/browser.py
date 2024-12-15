from __future__ import annotations

import asyncio
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
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0", locale="en-US"
        )

    async def get_search_url(self, name: str, page: int = 1) -> str:
        """
        Construct the search URL for a given query and page number.
        """
        return f"{self.url_suffix}search/{'+'.join(name.split())}/{page}/"

    async def get_torrents(self, page: browser.Page) -> list[TorrentData]:
        """
        Retrieve a list of TorrentData items from the currently loaded search results page,
        then fetch their magnet links in parallel.
        """
        log.debug("Begin parsing torrents from page...")
        rows = await self._get_torrent_rows(page)
        results: list[TorrentData] = []

        # First, parse all torrent rows to get their basic info and detail_url
        row_tasks = [self._extract_torrent_data_from_row(idx, row) for idx, row in enumerate(rows)]
        parsed_rows = await asyncio.gather(*row_tasks)
        results = [item for item in parsed_rows if item is not None]

        # Now fetch magnet links for all torrents that have detail_url
        await self._fetch_all_magnet_links(results)

        log.debug(f"Total parsed torrents with magnet links: {len(results)}")
        return results

    async def _get_torrent_rows(self, page: browser.Page):
        """
        Wait for and return all torrent rows in the search results table.
        """
        log.debug("Waiting for table rows to appear...")
        await page.wait_for_selector("table.table-list tbody tr")
        rows = await page.query_selector_all("table.table-list tbody tr")
        log.debug(f"Found {len(rows)} table rows.")
        return rows

    async def _extract_torrent_data_from_row(self, idx: int, row: browser.ElementHandle) -> TorrentData | None:
        """
        Extract torrent data from a single table row element.
        Returns a TorrentData object or None if extraction fails.
        """
        log.debug(f"Processing row {idx}...")

        # Fetch required cells
        cells = await self._fetch_cell_elements(row)
        if not cells:
            log.debug(f"Skipping row {idx}, missing required cells.")
            return None

        name_td, seeds_td, leeches_td, date_td, size_td, uploader_td = cells

        # Extract all needed text and links concurrently
        try:
            (name_text, detail_href, seeds_text, leeches_text, date_text, size_text, uploader_text) = (
                await self._fetch_cell_texts(name_td, seeds_td, leeches_td, date_td, size_td, uploader_td)
            )

            # Convert seeds and leeches to int
            seeds_value = self._to_int(seeds_text)
            leeches_value = self._to_int(leeches_text)

            item = TorrentData(
                name=name_text,
                seeds=seeds_value,
                leeches=leeches_value,
                uploaded_at=date_text.strip(),
                size=size_text.strip(),
                uploader=uploader_text.strip(),
                detail_url=detail_href,
                magnet_link="",  # Will be filled later
            )
            log.debug(f"Row {idx} processed: {item}")
            return item
        except Exception as e:
            log.warning(f"Failed to process row {idx}: {e}")
            return None

    async def _fetch_cell_elements(self, row: browser.ElementHandle):
        """
        Fetch all required cell elements from a row concurrently.
        Returns a tuple of cell elements or None if any are missing.
        """
        tasks = [
            row.query_selector("td.coll-1.name"),
            row.query_selector("td.coll-2.seeds"),
            row.query_selector("td.coll-3.leeches"),
            row.query_selector("td.coll-date"),
            row.query_selector("td.coll-4"),
            row.query_selector("td.coll-5"),
        ]
        cells = await asyncio.gather(*tasks)
        if any(c is None for c in cells):
            return None
        return cells

    async def _fetch_cell_texts(
        self,
        name_td: browser.ElementHandle,
        seeds_td: browser.ElementHandle,
        leeches_td: browser.ElementHandle,
        date_td: browser.ElementHandle,
        size_td: browser.ElementHandle,
        uploader_td: browser.ElementHandle,
    ):
        """
        Fetch all relevant texts and the detail URL concurrently.
        """
        # Parallel fetch of name and uploader links
        name_link_task = name_td.query_selector("a:nth-of-type(2)")
        uploader_link_task = uploader_td.query_selector("a")
        name_link, uploader_link = await asyncio.gather(name_link_task, uploader_link_task)

        # Prepare tasks for text extraction
        name_text_task = name_link.inner_text() if name_link else name_td.inner_text()
        seeds_text_task = seeds_td.inner_text()
        leeches_text_task = leeches_td.inner_text()
        date_text_task = date_td.inner_text()
        size_text_task = size_td.inner_text()
        uploader_text_task = uploader_link.inner_text() if uploader_link else uploader_td.inner_text()

        # Run text extraction in parallel
        (name_text_raw, seeds_text_raw, leeches_text_raw, date_text_raw, size_text_raw, uploader_text_raw) = (
            await asyncio.gather(
                name_text_task, seeds_text_task, leeches_text_task, date_text_task, size_text_task, uploader_text_task
            )
        )

        # Clean extracted text
        name_text = name_text_raw.strip()
        seeds_text = seeds_text_raw.strip()
        leeches_text = leeches_text_raw.strip()
        date_text = date_text_raw.strip()
        size_text = size_text_raw.strip()
        uploader_text = uploader_text_raw.strip()

        # Extract detail href if available
        detail_href = ""
        if name_link:
            href = await name_link.get_attribute("href")
            if href and href.startswith("/"):
                detail_href = f"https://1337x.to{href}"

        return name_text, detail_href, seeds_text, leeches_text, date_text, size_text, uploader_text

    @staticmethod
    def _to_int(value: str) -> int:
        """
        Safely convert a string to an integer, stripping commas and whitespace.
        Defaults to 0 if conversion fails.
        """
        try:
            return int(value.replace(",", "").strip())
        except:
            return 0

    async def _fetch_all_magnet_links(self, torrents: list[TorrentData]):
        """
        Fetch magnet links for all torrents with a detail_url in parallel.
        """
        log.debug("Fetching magnet links for all torrents...")
        tasks = []
        for t in torrents:
            if t.detail_url:
                tasks.append(self._fetch_magnet_link_for_torrent(t))

        if not tasks:
            log.debug("No torrents with detail URLs found.")
            return

        await asyncio.gather(*tasks)
        log.debug("All magnet links fetched.")

    async def _fetch_magnet_link_for_torrent(self, torrent: TorrentData):
        """
        Fetch the magnet link for a single torrent by opening its detail page.
        """
        log.debug(f"Fetching magnet link for torrent: {torrent.name}")
        page = await self.new_page()
        await page.goto(torrent.detail_url)

        # Wait for the magnet link element
        await page.wait_for_selector("a#openPopup")

        # Extract magnet link from href attribute
        magnet_link = await page.get_attribute("a#openPopup", "href")
        torrent.magnet_link = magnet_link if magnet_link else ""

        log.debug(f"Magnet link for {torrent.name}: {torrent.magnet_link}")

        # Close the page to free resources
        await page.close()
