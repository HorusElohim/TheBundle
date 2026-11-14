# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""Discord commands for Marvel Rivals ranked statistics."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING
from urllib.parse import quote

import discord
from discord import app_commands
from discord.ext import commands

from bundle.core import logger, tracer
from bundle.marvel_rivals.client import Champion, MarvelRivalsClient, MarvelRivalsError, PlayerStats

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

        async def run():
            return self._embed(self.bot, await self.client.player(uid, season=season))

        await self._reply(ctx, run)

    async def _reply(self, ctx: commands.Context, operation: Callable[[], Awaitable[discord.Embed]]) -> None:
        """Shared error boundary for all public-stat commands."""
        await ctx.defer()
        try:
            embed = await operation()
        except MarvelRivalsError as exc:
            embed = self.bot.embeds.error(title="Marvel Rivals", description=str(exc))
        except Exception:
            log.exception("Marvel Rivals lookup failed")
            embed = self.bot.embeds.error(title="Marvel Rivals", description="Could not retrieve Marvel Rivals data.")
        await ctx.send(embed=embed)

    def _champions_embed(self, heroes: list[Champion], role: str | None, page: int) -> discord.Embed:
        if role:
            heroes = [hero for hero in heroes if hero.category.casefold() == role.casefold()]
        pages = max(1, (len(heroes) + 19) // 20)
        if not 1 <= page <= pages:
            raise MarvelRivalsError(f"Choose a page between 1 and {pages}.")
        rows = [
            f"{hero.id} · {discord.utils.escape_markdown(hero.name)} ({discord.utils.escape_markdown(hero.category)})"
            for hero in heroes[(page - 1) * 20 : page * 20]
        ]
        return self.bot.embeds.info(
            title="Marvel Rivals · Champions",
            description="\n".join(rows) or "No heroes found for this role.",
            fields={"Heroes": str(len(heroes)), "Page": f"{page}/{pages}"},
        )

    async def _show_champions(self, ctx: commands.Context, role: str | None, page: int) -> None:
        async def run():
            return self._champions_embed(await self.client.champions(), role, page)

        await self._reply(ctx, run)

    @mr.command(name="champions")
    @app_commands.describe(role="Filter by Vanguard, Duelist, or Strategist", page="Page number (20 heroes per page)")
    async def champions(self, ctx: commands.Context, role: str | None = None, page: int = 1) -> None:
        """List playable heroes and their IDs."""
        await self._show_champions(ctx, role, page)

    @mr.group(name="c", invoke_without_command=True)
    async def c(self, ctx: commands.Context) -> None:
        """Champion shortcuts: list and stats."""
        await ctx.send(embed=self.bot.embeds.info(title="Marvel Rivals", description="Use /mr c list or /mr c stats."))

    @c.command(name="list")
    @app_commands.describe(role="Filter by role", page="Page number")
    async def c_list(self, ctx: commands.Context, role: str | None = None, page: int = 1) -> None:
        """List playable heroes."""
        await self._show_champions(ctx, role, page)

    @c.command(name="stats")
    @app_commands.describe(query="Hero name or numeric hero ID")
    async def c_stats(self, ctx: commands.Context, query: str) -> None:
        """Show available aggregate hero statistics."""

        async def run():
            hero = await self.client.champion_stats(query)
            fields = {
                "Matches": f"{hero.matches:,}",
                "Wins": f"{hero.wins:,}",
                "Win rate": f"{hero.win_rate:.1f}%" if hero.win_rate is not None else "—",
                "K / D / A": f"{hero.kills:,} / {hero.deaths:,} / {hero.assists:,}",
                "Damage": f"{hero.total_hero_damage:,}",
                "Healing": f"{hero.total_hero_heal:,}",
                "Damage taken": f"{hero.total_damage_taken:,}",
            }
            return self.bot.embeds.info(
                title=f"Marvel Rivals · {discord.utils.escape_markdown(hero.name)}",
                description=f"Hero ID: {hero.id}\nProvider aggregate · no season filter",
                fields=fields,
            )

        await self._reply(ctx, run)

    @mr.command(name="updates")
    async def updates(self, ctx: commands.Context) -> None:
        """Latest game patches, including hero and balance changes."""

        async def run():
            patches = await self.client.updates()
            rows = [
                f"**{discord.utils.escape_markdown(patch.title)}** · {patch.date}\n"
                f"{discord.utils.escape_markdown(patch.summary[:180])}"
                for patch in patches
            ]
            return self.bot.embeds.info(
                title="Marvel Rivals · Updates",
                description="\n\n".join(rows) or "No updates found.",
            )

        await self._reply(ctx, run)

    @mr.command(name="meta")
    async def meta(self, ctx: commands.Context) -> None:
        """Current balance context and live season win/pick/ban rankings."""

        async def run():
            patches = await self.client.balances()
            rows = [
                f"**{discord.utils.escape_markdown(patch.title)}** · {patch.date}\n"
                f"{discord.utils.escape_markdown(patch.summary[:160])}"
                for patch in patches
            ]
            return self.bot.embeds.info(
                title="Marvel Rivals · Meta watch",
                description=(
                    "**Latest balance changes**\n"
                    + ("\n\n".join(rows) or "No balance updates found.")
                    + "\n\n[View current-season win, pick, and ban rates](https://marvelrivals.gg/meta/)"
                    + "\n*Balance changes are not a statistical tier list.*"
                ),
            )

        await self._reply(ctx, run)
