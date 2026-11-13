# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""Discord commands for Marvel Rivals ranked statistics."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

import discord
from discord import app_commands
from discord.ext import commands

from bundle.core import logger, tracer
from bundle.marvel_rivals.client import MarvelRivalsClient, MarvelRivalsError, PlayerStats

if TYPE_CHECKING:
    from ..bot import Bot

log = logger.get_logger(__name__)


class MarvelRivalsCog(commands.Cog, name="marvel_rivals"):
    """The /mr command family and its HTTP client lifecycle."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.client = MarvelRivalsClient(bot.config.marvel_rivals_api_key or "")

    async def cog_unload(self) -> None:
        await self.client.close()

    @staticmethod
    def _embed(bot: Bot, stats: PlayerStats) -> discord.Embed:
        ranked = stats.ranked
        name = discord.utils.escape_mentions(discord.utils.escape_markdown(stats.name))
        profile = f"https://tracker.gg/marvel-rivals/profile/ign/{quote(stats.name, safe='')}/overview"
        if stats.season is not None:
            profile += f"?season={stats.season}"

        def fmt(value: float | None, spec: str = ".1f", unit: str = "") -> str:
            return f"{value:{spec}}{unit}" if value is not None else "—"

        fields = {
            "Rank": stats.rank or "Unranked",
            "Level": str(stats.level) if stats.level is not None else "—",
            "Matches": f"{ranked.matches:,}",
            "Wins": f"{ranked.wins:,}",
            "Win rate": fmt(ranked.win_rate, unit="%"),
            "KDA": fmt(ranked.kda, ".2f"),
            "K / D / A": f"{ranked.kills:,} / {ranked.deaths:,} / {ranked.assists:,}",
            "MVPs": f"{ranked.mvps:,}",
        }
        heroes = "\n".join(
            f"**{discord.utils.escape_markdown(hero.name)}** — {hero.matches} matches · {fmt(hero.win_rate, unit='%')} wins"
            for hero in stats.top_heroes
        )
        season = f"Season {stats.season}" if stats.season is not None else "Current season"
        return bot.embeds.info(
            title=f"Marvel Rivals · {name}",
            description=(
                f"**Ranked · {season}**\nUID: {stats.uid}\n"
                f"[View Tracker.gg profile]({profile})\n\n"
                f"**Top heroes**\n{heroes or 'No ranked hero data available.'}"
            ),
            fields=fields,
        )

    @commands.hybrid_group(name="mr", invoke_without_command=True)
    async def mr(self, ctx: commands.Context) -> None:
        """Marvel Rivals player commands."""
        await ctx.send(embed=self.bot.embeds.info(title="Marvel Rivals", description="Use /mr stats to look up a player."))

    @mr.command(name="stats")
    @app_commands.describe(uid="Numeric player UID", season="Season ID (defaults to current)")
    @tracer.Async.decorator.call_raise
    async def stats(self, ctx: commands.Context, uid: str, season: int | None = None) -> None:
        """Show ranked stats for a Marvel Rivals player."""
        await ctx.defer()
        try:
            player = await self.client.player(uid, season=season)
            embed = self._embed(self.bot, player)
        except MarvelRivalsError as exc:
            embed = self.bot.embeds.error(title="Marvel Rivals", description=str(exc))
        except Exception:
            log.exception("Marvel Rivals lookup failed for UID %s", uid)
            embed = self.bot.embeds.error(title="Marvel Rivals", description="Could not retrieve player stats.")
        await ctx.send(embed=embed)
