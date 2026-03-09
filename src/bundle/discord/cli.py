"""CLI for the Discord bot module."""

import os

import rich_click as click

from bundle.core import logger, tracer
from bundle.discord.bot import BotConfig, run_bot

log = logger.get_logger(__name__)


@click.group(name="discord")
def discord():
    """Discord bot commands."""
    pass


@discord.command()
@click.option("--token", envvar="DISCORD_BOT_TOKEN", default=None, help="Bot token (or set DISCORD_BOT_TOKEN env var).")
@click.option("--prefix", default="!", help="Command prefix.")
@tracer.Sync.decorator.call_raise
async def start(token: str | None, prefix: str):
    """Start the Discord bot."""
    if not token:
        token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        log.error("No bot token provided. Use --token or set DISCORD_BOT_TOKEN env var.")
        raise click.Abort()

    config = BotConfig(token=token, command_prefix=prefix)
    await run_bot(config)
