# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

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
