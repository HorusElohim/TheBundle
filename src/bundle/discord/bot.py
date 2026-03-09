"""Core Discord bot implementation."""

from __future__ import annotations

import discord
from discord.ext import commands

from bundle.core import data, logger, tracer

log = logger.get_logger(__name__)


class BotConfig(data.Data):
    """Configuration for the Discord bot."""

    token: str
    command_prefix: str = "!"
    intents_message_content: bool = True


class Bot(commands.Bot):
    """TheBundle Discord bot."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        intents = discord.Intents.default()
        intents.message_content = config.intents_message_content
        super().__init__(command_prefix=config.command_prefix, intents=intents)

    @tracer.Async.decorator.call_raise
    async def on_ready(self) -> None:
        log.info(f"Bot connected as {self.user} (id={self.user.id})")
        log.info(f"Guilds: {[g.name for g in self.guilds]}")

    async def setup_hook(self) -> None:
        """Called after login, before processing events. Load cogs here."""
        await self.add_cog(CoreCog(self))
        log.info(f"Loaded {len(self.cogs)} cog(s): {list(self.cogs.keys())}")


class CoreCog(commands.Cog, name="core"):
    """Built-in commands."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def ping(self, ctx: commands.Context) -> None:
        """Check bot responsiveness."""
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(f"pong ({latency_ms}ms)")


async def run_bot(config: BotConfig) -> None:
    """Create and run the Discord bot."""
    bot = Bot(config)
    log.info("Starting Discord bot...")
    await bot.start(config.token)
