"""Core utility commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from bundle.core import logger, tracer

if TYPE_CHECKING:
    from ..bot import Bot

log = logger.get_logger(__name__)


class CoreCog(commands.Cog, name="core"):
    """Built-in utility commands."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.hybrid_command()
    @tracer.Async.decorator.call_raise
    async def ping(self, ctx: commands.Context) -> None:
        """Check bot responsiveness."""
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(f"{self.bot.brand_name} pong ({latency_ms}ms)")
