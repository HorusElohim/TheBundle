"""Bot lifecycle events: online/offline announcements."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bundle.core import logger, tracer

if TYPE_CHECKING:
    from ..bot import Bot

log = logger.get_logger(__name__)


class LifecycleCog(commands.Cog, name="lifecycle"):
    """Announces bot online/offline status in the dedicated bot channel."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    @tracer.Async.decorator.call_raise
    async def on_ready(self) -> None:
        latency_ms = round(self.bot.latency * 1000)
        for guild in self.bot.guilds:
            channel = await self.bot.bot_channel(guild)
            await channel.send(embed=self.bot.embeds.online(self.bot.user, len(self.bot.guilds), latency_ms))
            log.info(f"Sent online announcement in #{channel.name} ({guild.name})")

    async def cog_unload(self) -> None:
        for guild in self.bot.guilds:
            try:
                channel = await self.bot.bot_channel(guild)
                await channel.send(embed=self.bot.embeds.offline())
                log.info(f"Sent offline announcement in #{channel.name} ({guild.name})")
            except discord.HTTPException as exc:
                log.warning(f"Could not send offline message to {guild.name}: {exc}")
