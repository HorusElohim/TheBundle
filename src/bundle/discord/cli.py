"""CLI for the Discord bot module."""

import os

import rich_click as click

from bundle.core import logger, tracer

from .bot import BotConfig, run_bot

log = logger.get_logger(__name__)


@click.group(name="discord")
def discord():
    """Discord bot commands."""
    pass


@discord.command()
@click.option(
    "--name",
    "bot_name",
    envvar="DISCORD_BOT_NAME",
    default=None,
    help="Bot name used for logs and the dedicated guild channel (or set DISCORD_BOT_NAME).",
)
@click.option("--token", envvar="DISCORD_BOT_TOKEN", default=None, help="Bot token (or set DISCORD_BOT_TOKEN env var).")
@click.option("--prefix", envvar="DISCORD_BOT_PREFIX", default="!", help="Command prefix (or set DISCORD_BOT_PREFIX).")
@tracer.Sync.decorator.call_raise
async def start(bot_name: str | None, token: str | None, prefix: str):
    """Start the Discord bot."""
    bot_name = (bot_name or os.environ.get("DISCORD_BOT_NAME") or "Bundle Bot").strip() or "Bundle Bot"
    if not token:
        token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        log.error("No bot token provided. Use --token or set DISCORD_BOT_TOKEN env var.")
        raise click.Abort()

    config = BotConfig(token=token, bot_name=bot_name, command_prefix=prefix)
    await run_bot(config)
