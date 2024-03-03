# example_usage.py
import asyncio
from bundle.core.browser import Browser
from bundle.core.logger import setup_root_logger

# Configure logging
logger = setup_root_logger(__name__)


async def main():
    try:
        async with Browser.webkit(headless=False) as browser:
            page = await browser.new_page()
            await asyncio.sleep(10)  # Simulate some browser operations
    except asyncio.CancelledError:
        logger.info("Main operation was cancelled.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Initiating graceful shutdown...")
