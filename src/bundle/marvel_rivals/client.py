# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""Typed Marvel Rivals player statistics and a reusable HTTP client."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from pydantic import AliasChoices, AliasPath, Field, ValidationError

from bundle.core import data, tracer

API_BASE_URL = "https://marvelrivalsapi.com/api/v1"


class MarvelRivalsError(RuntimeError):
    """A player lookup failed without exposing provider internals."""


class MatchStats(data.Data):
    """Shared combat statistics for ranked matches and individual heroes."""

    model_config = data.configuration(extra="ignore")

    matches: int = Field(0, validation_alias=AliasChoices("total_matches", "matches"))
    wins: int = Field(0, validation_alias=AliasChoices("total_wins", "wins"))
    kills: int = Field(0, validation_alias=AliasChoices("total_kills", "kills"))
    deaths: int = Field(0, validation_alias=AliasChoices("total_deaths", "deaths"))
    assists: int = Field(0, validation_alias=AliasChoices("total_assists", "assists"))
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


class PlayerStats(data.Data):
    """Player overview with aliases for the API's nested response shape."""

    model_config = data.configuration(extra="ignore")

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


class MarvelRivalsClient:
    """Authenticated player lookups over one pooled HTTP session."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session = aiohttp.ClientSession(
            headers={"x-api-key": api_key},
            timeout=aiohttp.ClientTimeout(total=10),
        )

    async def close(self) -> None:
        await self.session.close()

    @tracer.Async.decorator.call_raise
    async def player(self, uid: str, *, season: int | None = None) -> PlayerStats:
        """Fetch ranked stats by numeric UID, optionally for a specific season."""
        if not (uid.isascii() and uid.isdecimal() and len(uid) <= 16):
            raise MarvelRivalsError("Enter a numeric Marvel Rivals UID (up to 16 digits).")
        if season is not None and not 1 <= season <= 99:
            raise MarvelRivalsError("Season must be between 1 and 99.")
        if not self.api_key:
            raise MarvelRivalsError("Set MARVEL_RIVALS_API_KEY to enable player lookups.")

        try:
            async with self.session.get(
                f"{API_BASE_URL}/player/{uid}",
                params={"season": season} if season is not None else None,
            ) as response:
                match response.status:
                    case 200:
                        return PlayerStats.from_api(await response.json(), season=season)
                    case 401 | 403:
                        raise MarvelRivalsError("Marvel Rivals API credentials were rejected.")
                    case 404:
                        raise MarvelRivalsError(f"No Marvel Rivals player found for UID {uid}.")
                    case 429:
                        raise MarvelRivalsError("Marvel Rivals API rate limit reached. Try again later.")
                    case status:
                        raise MarvelRivalsError(f"Marvel Rivals API unavailable (HTTP {status}).")
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise MarvelRivalsError("Marvel Rivals API unavailable or returned invalid JSON.") from exc
