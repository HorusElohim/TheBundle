from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from playwright.async_api import Frame, Page, Request

from bundle.core import browser, data, entity, logger, tracer

log = logger.get_logger(__name__)

DEFAULT_EMBED_URL = "https://www.youtube-nocookie.com/embed/ouEl3qTLc0M?autoplay=1&mute=1"
REFERER_ORIGIN = "https://bundle.local"
REFERER_URL = f"{REFERER_ORIGIN}/youtube/token"


def build_embed_url(embed_url: str) -> str:
    parsed = urlparse(embed_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["origin"] = REFERER_ORIGIN
    query.setdefault("enablejsapi", "1")
    encoded_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=encoded_query))


class PotoTokenEntity(entity.Entity):
    """Entity holding the extracted poto token and visitor data."""

    name: str = data.Field(default="unknow")
    potoken: str = data.Field(default="unknow")
    visitor_data: str = data.Field(default="unknow")


class PotoTokenBrowser(browser.Browser):
    """
    Extension of the Playwright-based Browser that implements poto token extraction.
    """

    # Initialize with a default empty token entity and an asyncio event to signal extraction.
    token_info: PotoTokenEntity = data.Field(default_factory=PotoTokenEntity)
    extraction_event: asyncio.Event = data.Field(default_factory=asyncio.Event)

    @tracer.Async.decorator.call_raise
    async def handle_request(self, request: Request) -> None:
        """
        Inspect outgoing requests and extract the poto token if the request matches the expected criteria.
        """
        if request.method != "POST" or "/youtubei/v1/player" not in request.url:
            return

        post_data = request.post_data
        if not post_data:
            return

        try:
            payload = json.loads(post_data)
            visitor_data = payload["context"]["client"]["visitorData"]
            potoken = payload["serviceIntegrityDimensions"]["poToken"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning(f"Token extraction failed: {e}")
            return

        # Update the token entity and signal that extraction is complete.
        self.token_info = PotoTokenEntity(name="real", potoken=potoken, visitor_data=visitor_data)
        log.info(f"Extracted new token: {self.token_info}")
        self.extraction_event.set()

    @tracer.Async.decorator.call_raise
    async def click_player(self, page: Page, timeout: float = 10_000) -> None:
        """
        Wait for the video player element and click it to trigger the token request.
        """
        search_contexts: list[Page | Frame] = [page]
        search_contexts.extend(frame for frame in page.frames if frame != page.main_frame)

        for context in search_contexts:
            player, exception = await tracer.Async.call(context.wait_for_selector, "#movie_player", timeout=timeout)
            if exception:
                continue
            await player.click()
            return

        log.warning("Unable to locate video player in any frame.")

    async def wait_for_extraction(self, timeout: float = 30.0) -> None:
        """
        Wait until the extraction event is set, indicating that token extraction is complete.
        """
        await asyncio.wait_for(self.extraction_event.wait(), timeout=timeout)

    @tracer.Async.decorator.call_raise
    async def extract_token(self, url: str | None = None, timeout: float = 30.0) -> PotoTokenEntity:
        """
        Orchestrates the token extraction process.

        Steps:
          1. Open a new page.
          2. Attach the request handler to capture outgoing requests.
          3. Navigate to the target URL.
          4. Click the video player element to trigger the token request.
          5. Wait for the token extraction to complete.
          6. Close the page and return the extracted token.

        Args:
            url: The YouTube embed URL for token extraction.
            timeout: Maximum time (in seconds) to wait for the extraction process.

        Returns:
            A PotoTokenEntity with the extracted token data, or None if extraction times out.
        """
        embed_url = build_embed_url(url or DEFAULT_EMBED_URL)
        page: Page = await self.new_page()

        # Step 1: Listen for outgoing requests.
        page.on("request", self.handle_request)

        # Step 2: Navigate to the target URL with an explicit referer, satisfying YouTube's client identity checks.
        await page.goto(embed_url, referer=REFERER_URL, wait_until="domcontentloaded")

        # Step 3: Click on the video player element.
        await self.click_player(page)

        # Step 4: Wait until the token is extracted.
        _, exception = await tracer.Async.call(self.wait_for_extraction, timeout=timeout)

        if exception:
            log.warning("Timeout waiting for token extraction.")

        await page.close()
        return self.token_info


if __name__ == "__main__":

    async def run():
        async with PotoTokenBrowser.chromium(headless=False) as ptb:
            return await ptb.extract_token()

    poto_token = asyncio.get_event_loop().run_until_complete(run())
    log.info("PotoToken:\n%s", poto_token)
