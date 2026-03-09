"""Welcome new members joining a guild."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bundle.core import logger, tracer

if TYPE_CHECKING:
    from bundle.discord.bot import Bot

log = logger.get_logger(__name__)


class GreetCog(commands.Cog, name="greet"):
    """Welcomes new members in the guild's system channel or the bot channel."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    @tracer.Async.decorator.call_raise
    async def on_member_join(self, member: discord.Member) -> None:
        channel = member.guild.system_channel or await self.bot.bot_channel(member.guild)
        await channel.send(f"Welcome to **{member.guild.name}**, {member.mention}!")
        log.info(f"Welcomed {member} in #{channel.name} ({member.guild.name})")
