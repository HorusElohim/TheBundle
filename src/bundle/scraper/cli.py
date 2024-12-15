import asyncio
from pathlib import Path

import asyncclick as click

from bundle.scraper import log, sites


@click.group()
def cli():
    pass


@click.group()
def torrent():
    pass


@torrent.command()
@click.argument("name", type=str)
async def search(name: str):
    lib = sites.site_1337
    log.info(f"Searching {name} in 1337 ...")
    async with lib.Browser.chromium(headless=True) as browser:
        # Just to make the linter happy
        assert isinstance(browser, lib.Browser)

        await browser.set_context()
        page = await browser.new_page()
        url_1 = await browser.get_search_url(name, page=1)
        await page.goto(url_1)
        # Now parse the table
        torrents = await browser.get_torrents(page)
        for torrent in torrents:
            log.info(await torrent.as_json())

        await asyncio.sleep(10)


cli.add_command(torrent)
