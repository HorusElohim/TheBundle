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

import pytest
from typing import Type
from bundle.core.browser import Browser, BrowserType
from playwright.async_api import Page


# Mark all tests in this module as asynchronous
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
async def playwright_instance():
    """
    Fixture to start Playwright once per test session.
    """
    from playwright.async_api import async_playwright

    playwright = await async_playwright().start()
    yield playwright
    await playwright.stop()


@pytest.mark.parametrize(
    "browser_cls, browser_type",
    [
        (Browser.chromium, BrowserType.CHROMIUM),
        (Browser.firefox, BrowserType.FIREFOX),
        (Browser.webkit, BrowserType.WEBKIT),
    ],
)
async def test_browser_instantiation(browser_cls: Type[Browser], browser_type):
    """
    Test instantiation of Browser using class methods.
    """
    async with browser_cls(name=browser_type.value, headless=True) as browser:
        assert browser.browser_type == browser_type
        assert browser.headless is True
        assert browser.is_closed is False
        assert browser.browser is not None
        assert len(browser.contexts) == 0
        # Test new page
        page = await browser.new_page()
        assert isinstance(page, Page)
        assert len(browser.contexts) == 1
        # Test navigate
        await page.goto("https://example.com")
        title = await page.evaluate("document.title")
        assert title == "Example Domain"
    # After context, browser should be closed
    assert browser.is_closed
    assert browser.browser is None
    assert len(browser.contexts) == 0
