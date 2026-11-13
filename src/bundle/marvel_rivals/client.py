# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""Typed Marvel Rivals player statistics and a reusable HTTP client."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

import aiohttp
from pydantic import AliasChoices, AliasPath, Field, ValidationError

from bundle.core import data, tracer

API_BASE_URL = "https://marvelrivalsapi.com/api/v1"


class MarvelRivalsError(RuntimeError):
    """A player lookup failed without exposing provider internals."""


class MarvelData(data.Data):
    """API model with stable, canonical Data serialization."""

    model_config = data.configuration(extra="ignore") | {"validate_by_name": True}


class MatchStats(MarvelData):
    """Shared combat statistics for ranked matches and individual heroes."""

    matches: int = Field(0, validation_alias=AliasChoices("total_matches", "matches"))
    wins: int = Field(0, validation_alias=AliasChoices("total_wins", "wins"))
    kills: int = Field(0, validation_alias=AliasChoices("total_kills", "kills", "k"))
    deaths: int = Field(0, validation_alias=AliasChoices("total_deaths", "deaths", "d"))
    assists: int = Field(0, validation_alias=AliasChoices("total_assists", "assists", "a"))
    mvps: int = Field(0, validation_alias=AliasChoices("total_mvp", "mvp", "mvps"))

    @property
    def win_rate(self) -> float | None:
        return 100 * self.wins / self.matches if self.matches else None

    @property
    def kda(self) -> float | None:
        return (self.kills + self.assists) / max(self.deaths, 1) if self.matches else None


class HeroStats(MatchStats):
    """Hero performance shares the same combat model as ranked totals."""

    name: str = Field(validation_alias=AliasChoices("hero_name", "name"))
    play_time: int = 0


class PlayerStats(MarvelData):
    """Player overview with aliases for the API's nested response shape."""

    uid: int
    name: str = Field(validation_alias=AliasChoices("name", AliasPath("player", "name"), AliasPath("player", "nickname")))
    level: int | str | None = Field(None, validation_alias=AliasPath("player", "level"))
    rank: str | None = Field(None, validation_alias=AliasPath("player", "rank", "rank"))
    ranked: MatchStats = Field(validation_alias=AliasPath("overall_stats", "ranked"))
    heroes: list[HeroStats] = Field(default_factory=list, validation_alias="heroes_ranked")
    season: int | None = None

    @property
    def top_heroes(self) -> list[HeroStats]:
        return sorted(
            (hero for hero in self.heroes if hero.matches),
            key=lambda hero: (hero.play_time, hero.matches),
            reverse=True,
        )[:3]

    @classmethod
    def from_api(cls, payload: Any, *, season: int | None = None) -> PlayerStats:
        """Validate provider data without manual field-by-field copying."""
        match payload:
            case {"isPrivate": True} | {"player": {"isPrivate": True}}:
                raise MarvelRivalsError("This player's statistics are private.")
            case dict():
                try:
                    return cls.model_validate(payload | {"season": season})
                except ValidationError as exc:
                    raise MarvelRivalsError("Ranked statistics unavailable or invalid in the API response.") from exc
            case _:
                raise MarvelRivalsError("The player API returned an unexpected response.")


class Champion(MarvelData):
    """A playable hero from the public roster."""

    id: str | int
    name: str
    role: str = "Unknown"

    @property
    def category(self) -> str:
        match self.role.casefold():
            case "tank" | "vanguard":
                return "Vanguard"
            case "dps" | "duelist":
                return "Duelist"
            case "support" | "strategist":
                return "Strategist"
            case _:
                return self.role


class ChampionStats(MatchStats):
    """Global hero totals; the API does not provide a season filter."""

    name: str = Field(validation_alias=AliasChoices("hero_name", "name"))
    id: str | int = Field(validation_alias=AliasChoices("hero_id", "id"))
    total_hero_damage: int = 0
    total_hero_heal: int = 0
    total_damage_taken: int = 0


class Patch(MarvelData):
    """A dated game or balance update."""

    title: str = Field(validation_alias=AliasChoices("patchTitle", "title"))
    date: str = Field(validation_alias=AliasChoices("patchDate", "date"))
    summary: str = Field("", validation_alias=AliasChoices("previewText", "overview"))
    kind: str = Field("Patch", validation_alias=AliasChoices("patchType", "kind"))


class MarvelRivalsClient:
    """One lazy HTTP connection pool shared by every bot command."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session: aiohttp.ClientSession | None = None

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    @tracer.Async.decorator.call_raise
    async def _get(self, path: str, *, params: dict[str, int] | None = None) -> Any:
        if not self.api_key:
            raise MarvelRivalsError("Set MARVEL_RIVALS_API_KEY to enable Marvel Rivals commands.")
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"x-api-key": self.api_key},
                timeout=aiohttp.ClientTimeout(total=10),
            )
        try:
            async with self.session.get(f"{API_BASE_URL}/{path}", params=params) as response:
                match response.status:
                    case 200:
                        return await response.json()
                    case 401 | 403:
                        raise MarvelRivalsError("Marvel Rivals API credentials were rejected.")
                    case 404:
                        raise MarvelRivalsError("Marvel Rivals resource not found.")
                    case 429:
                        raise MarvelRivalsError("Marvel Rivals API rate limit reached. Try again later.")
                    case status:
                        raise MarvelRivalsError(f"Marvel Rivals API unavailable (HTTP {status}).")
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise MarvelRivalsError("Marvel Rivals API unavailable or returned invalid JSON.") from exc

    async def player(self, uid: str, *, season: int | None = None) -> PlayerStats:
        """Retrieve ranked statistics by numeric player UID."""
        if not (uid.isascii() and uid.isdecimal() and len(uid) <= 16):
            raise MarvelRivalsError("Enter a numeric Marvel Rivals UID (up to 16 digits).")
        if season is not None and not 1 <= season <= 99:
            raise MarvelRivalsError("Season must be between 1 and 99.")
        payload = await self._get(f"player/{uid}", params={"season": season} if season is not None else None)
        return PlayerStats.from_api(payload, season=season)

    async def champions(self) -> list[Champion]:
        """All known playable heroes sorted by name."""
        match await self._get("heroes"):
            case {"heroes": list() as rows}:
                return self._champion_rows(rows)
            case list() as rows:
                return self._champion_rows(rows)
            case _:
                raise MarvelRivalsError("Hero catalogue is unavailable.")

    @staticmethod
    def _champion_rows(rows: list) -> list[Champion]:
        try:
            return sorted([Champion.model_validate(row) for row in rows], key=lambda hero: hero.name.casefold())
        except ValidationError as exc:
            raise MarvelRivalsError("Hero catalogue has an unexpected format.") from exc

    async def champion_stats(self, query: str) -> ChampionStats:
        """Global hero aggregates by name or numeric ID."""
        if not query.strip() or len(query) > 64:
            raise MarvelRivalsError("Provide a hero name or numeric ID (up to 64 characters).")
        payload = await self._get(f"heroes/hero/{quote(query.strip(), safe='')}/stats")
        try:
            return ChampionStats.model_validate(payload)
        except ValidationError as exc:
            raise MarvelRivalsError("Hero statistics have an unexpected format.") from exc

    async def _patches(self, endpoint: str, limit: int) -> list[Patch]:
        match await self._get(endpoint, params={"page": 1, "limit": limit}):
            case {"formatted_patches": list() as rows}:
                try:
                    return [Patch.model_validate(row) for row in rows]
                except ValidationError as exc:
                    raise MarvelRivalsError("Patch notes have an unexpected format.") from exc
            case _:
                raise MarvelRivalsError("Patch notes are unavailable.")

    async def updates(self, limit: int = 5) -> list[Patch]:
        """Recent game updates and balance releases, newest first."""
        patches, balances = await asyncio.gather(
            self._patches("patch-notes", limit),
            self._patches("balances", limit),
        )
        return sorted(patches + balances, key=lambda item: item.date, reverse=True)[:limit]

    async def balances(self, limit: int = 3) -> list[Patch]:
        """Balance notes, not invented statistical win/pick rates."""
        return sorted(await self._patches("balances", limit), key=lambda item: item.date, reverse=True)
