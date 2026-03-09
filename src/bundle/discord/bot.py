"""Core Discord bot implementation."""

from __future__ import annotations

import discord
from discord.ext import commands

from bundle.core import data, logger, tracer
from bundle.discord.cogs.core import CoreCog
from bundle.discord.cogs.greet import GreetCog
from bundle.discord.cogs.lifecycle import LifecycleCog

log = logger.get_logger(__name__)


BOT_CHANNEL_NAME = "bundle-bot"


class BotConfig(data.Data):
    """Configuration for the Discord bot."""

    token: str
    command_prefix: str = "!"
    intents_message_content: bool = True
    intents_members: bool = True


class Bot(commands.Bot):
    """TheBundle Discord bot."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        intents = discord.Intents.default()
        intents.message_content = config.intents_message_content
        intents.members = config.intents_members
        super().__init__(command_prefix=config.command_prefix, intents=intents)

    async def bot_channel(self, guild: discord.Guild) -> discord.TextChannel:
        """Get or create the dedicated bot channel for a guild."""
        channel = discord.utils.get(guild.text_channels, name=BOT_CHANNEL_NAME)
        if channel is None:
            log.info(f"Creating #{BOT_CHANNEL_NAME} in {guild.name}")
            channel = await guild.create_text_channel(BOT_CHANNEL_NAME, topic="TheBundle bot announcements")
        return channel

    @tracer.Async.decorator.call_raise
    async def on_ready(self) -> None:
        log.info(f"Bot connected as {self.user} (id={self.user.id})")
        log.info(f"Guilds: {[g.name for g in self.guilds]}")

    async def setup_hook(self) -> None:
        """Load all cogs."""
        for cog in (CoreCog(self), GreetCog(self), LifecycleCog(self)):
            await self.add_cog(cog)
        log.info(f"Loaded {len(self.cogs)} cog(s): {list(self.cogs.keys())}")


async def run_bot(config: BotConfig) -> None:
    """Create and run the Discord bot."""
    bot = Bot(config)
    log.info("Starting Discord bot...")
    async with bot:
        await bot.start(config.token)
