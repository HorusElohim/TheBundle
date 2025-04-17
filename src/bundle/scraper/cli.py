import rich_click as click

from bundle.core import logger, tracer
from bundle.scraper import sites

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def scraper():
    pass


@click.group()
@tracer.Sync.decorator.call_raise
async def torrent():
    pass


@torrent.command()
@click.argument("name", type=str)
@tracer.Sync.decorator.call_raise
async def search(name: str):
    lib = sites.site_1337
    log.info(f"Searching {name} in 1337 ...")
    async with lib.Browser.chromium(headless=True) as browser:
        # Just to make the linter happy
        assert isinstance(browser, lib.Browser)

        await browser.set_context()
        page = await browser.new_page()
        url_1 = await browser.get_search_url(name, page=1)
        await page.goto(url_1, wait_until="commit")
        torrents = await browser.get_torrents(page)
        log.info(await browser.tabulate_torrents(torrents))


scraper.add_command(torrent)
