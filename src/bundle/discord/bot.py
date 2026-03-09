"""Core Discord bot implementation."""

from __future__ import annotations

import re

import discord
from discord.ext import commands

from bundle.core import data, logger, tracer

from .cogs.core import CoreCog
from .cogs.greet import GreetCog
from .cogs.lifecycle import LifecycleCog
from .cogs.music import MusicCog
from .cogs.youtube import YoutubeCog
from .embeds import EmbedFactory
from .help import BundleHelpCommand

log = logger.get_logger(__name__)


DEFAULT_BOT_NAME = "Bundle Bot"


def to_discord_channel_name(value: str) -> str:
    """Convert a display name into a Discord-safe text channel name."""

    channel_name = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return channel_name or "bundle-bot"


class BotConfig(data.Data):
    """Configuration for the Discord bot."""

    token: str
    bot_name: str = DEFAULT_BOT_NAME
    command_prefix: str = "!"
    intents_message_content: bool = True
    intents_members: bool = True

    @property
    def channel_name(self) -> str:
        return to_discord_channel_name(self.bot_name)


class Bot(commands.Bot):
    """TheBundle Discord bot."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self._tree_synced = False
        intents = discord.Intents.default()
        intents.message_content = config.intents_message_content
        intents.members = config.intents_members
        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
            help_command=BundleHelpCommand(),
        )

    @property
    def brand_name(self) -> str:
        return self.config.bot_name

    @property
    def brand_avatar_url(self) -> str | None:
        return self.user.display_avatar.url if self.user else None

    @property
    def embeds(self) -> EmbedFactory:
        """Embed factory pre-configured with the bot's brand identity."""
        return EmbedFactory(
            bot_name=self.brand_name,
            bot_avatar_url=self.brand_avatar_url or "",
        )

    async def bot_channel(self, guild: discord.Guild) -> discord.TextChannel:
        """Get or create the dedicated bot channel for a guild."""
        channel_name = self.config.channel_name
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if channel is None:
            log.info(f"Creating #{channel_name} in {guild.name}")
            channel = await guild.create_text_channel(channel_name, topic=f"{self.config.bot_name} announcements")
        return channel

    async def sync_guild_identity(self, guild: discord.Guild) -> None:
        """Best-effort sync of the bot nickname to the configured brand name."""
        me = guild.me
        if me is None or me.display_name == self.brand_name:
            return
        if not me.guild_permissions.change_nickname:
            log.debug("Cannot change nickname in %s; missing permission.", guild.name)
            return
        try:
            await me.edit(nick=self.brand_name)
            log.info("Updated bot nickname to '%s' in %s", self.brand_name, guild.name)
        except discord.HTTPException as exc:
            log.warning("Could not update bot nickname in %s: %s", guild.name, exc)

    @tracer.Async.decorator.call_raise
    async def on_ready(self) -> None:
        log.info(f"Bot connected as {self.user} (id={self.user.id})")
        log.info(f"Guilds: {[g.name for g in self.guilds]}")
        for guild in self.guilds:
            await self.sync_guild_identity(guild)
        await self._sync_tree()

    async def _sync_tree(self) -> None:
        """Sync slash commands to all guilds (once per session)."""
        if self._tree_synced:
            return
        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        self._tree_synced = True
        log.info("Synced slash commands to %d guild(s)", len(self.guilds))

    @tracer.Async.decorator.call_raise
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Sync slash commands when the bot joins a new guild."""
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        log.info("Synced slash commands to new guild: %s", guild.name)
        await self.sync_guild_identity(guild)

    async def setup_hook(self) -> None:
        """Load all cogs."""
        for cog in (CoreCog(self), GreetCog(self), LifecycleCog(self), YoutubeCog(self), MusicCog(self)):
            await self.add_cog(cog)
        log.info(f"Loaded {len(self.cogs)} cog(s): {list(self.cogs.keys())}")


async def run_bot(config: BotConfig) -> None:
    """Create and run the Discord bot."""
    bot = Bot(config)
    log.info("Starting Discord bot '%s'...", config.bot_name)
    async with bot:
        await bot.start(config.token)
