# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""Marvel Rivals API and Discord contracts, using TheBundle's Data test tools."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bundle.core import data
from bundle.marvel_rivals.client import (
    Champion,
    ChampionStats,
    HeroStats,
    MarvelRivalsClient,
    MarvelRivalsError,
    MatchStats,
    Patch,
    PlayerStats,
)

PLAYER = {
    "uid": 75978910,
    "name": "MarkNo1",
    "player": {"level": "42", "rank": {"rank": "Diamond"}},
    "overall_stats": {
        "ranked": {
            "total_matches": 20,
            "total_wins": 11,
            "total_kills": 200,
            "total_deaths": 100,
            "total_assists": 80,
            "total_mvp": 3,
        }
    },
    "heroes_ranked": [
        {"hero_name": "Luna Snow", "matches": 8, "wins": 5, "play_time": 900},
        {"hero_name": "Mantis", "matches": 12, "wins": 6, "play_time": 1500},
    ],
}
HEROES = [
    {"id": 1032, "name": "Doctor Strange", "role": "Tank"},
    {"id": 1001, "name": "Iron Man", "role": "DPS"},
    {"id": 1043, "name": "Luna Snow", "role": "Support"},
]


@pytest.fixture
def client() -> MarvelRivalsClient:
    return MarvelRivalsClient("test-key")


@pytest.mark.parametrize(
    ("model", "values"),
    [
        (MatchStats, {"matches": 2, "wins": 1}),
        (HeroStats, {"name": "Mantis", "matches": 3}),
        (PlayerStats, {"uid": 75978910, "name": "MarkNo1", "ranked": {"matches": 20}, "heroes": []}),
        (Champion, {"id": 1032, "name": "Doctor Strange", "role": "Tank"}),
        (ChampionStats, {"id": 1032, "name": "Doctor Strange", "matches": 5}),
        (Patch, {"title": "Balance update", "date": "2026-11-13"}),
    ],
    ids=["match", "hero", "player", "champion", "hero-stats", "patch"],
)
@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=10_000_000)
@pytest.mark.asyncio
async def test_data_contract(model: type[data.Data], values: dict) -> data.Data:
    """Profile construction and validate TheBundle's complete Data contract."""
    return model(**values)


def test_player_stats() -> None:
    stats = PlayerStats.from_api(PLAYER, season=21)
    assert (stats.uid, stats.name, stats.rank, stats.season) == (75978910, "MarkNo1", "Diamond", 21)
    assert (stats.ranked.win_rate, stats.ranked.kda) == (55, 2.8)
    assert [hero.name for hero in stats.top_heroes] == ["Mantis", "Luna Snow"]


def test_empty_stats() -> None:
    payload = deepcopy(PLAYER)
    payload["player"]["rank"] = None
    payload["overall_stats"]["ranked"] = {}
    payload["heroes_ranked"] = []
    stats = PlayerStats.from_api(payload)
    assert stats.rank is None
    assert stats.top_heroes == []
    assert stats.ranked.win_rate is None and stats.ranked.kda is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"isPrivate": True}, "private"),
        ({"player": {"isPrivate": True}}, "private"),
        ({"overall_stats": {}}, "Ranked"),
        ({"overall_stats": {"ranked": {"total_wins": "invalid"}}}, "invalid"),
    ],
)
def test_invalid_player(change: dict, message: str) -> None:
    with pytest.raises(MarvelRivalsError, match=message):
        PlayerStats.from_api(PLAYER | change)


def test_unexpected_player() -> None:
    with pytest.raises(MarvelRivalsError, match="unexpected"):
        PlayerStats.from_api([])


def test_metrics() -> None:
    assert MatchStats(matches=2, wins=1, kills=6, assists=4).kda == 10
    assert HeroStats(name="Mantis", matches=4, wins=3).win_rate == 75


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True])
async def test_champions(client: MarvelRivalsClient, wrapped: bool) -> None:
    client._get = AsyncMock(return_value={"heroes": HEROES} if wrapped else HEROES)
    champions = await client.champions()
    assert [hero.name for hero in champions] == ["Doctor Strange", "Iron Man", "Luna Snow"]
    assert [hero.category for hero in champions] == ["Vanguard", "Duelist", "Strategist"]
    client._get.assert_awaited_once_with("heroes")


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["Doctor Strange", "1032"])
async def test_champion_stats(client: MarvelRivalsClient, query: str) -> None:
    client._get = AsyncMock(
        return_value={
            "hero_id": 1032,
            "hero_name": "Doctor Strange",
            "matches": 10,
            "wins": 6,
            "k": 30,
            "d": 15,
            "a": 8,
        }
    )
    hero = await client.champion_stats(query)
    assert (hero.id, hero.win_rate, hero.kills, hero.deaths, hero.assists) == (1032, 60, 30, 15, 8)
    client._get.assert_awaited_once_with(f"heroes/hero/{query.replace(' ', '%20')}/stats")


@pytest.mark.asyncio
async def test_updates(client: MarvelRivalsClient) -> None:
    updates = {
        "patch-notes": [{"patchTitle": "New hero", "patchDate": "2026-11-13"}],
        "balances": [{"patchTitle": "Balance", "patchDate": "2026-11-12"}],
    }
    client._get = AsyncMock(side_effect=lambda path, **_: {"formatted_patches": updates[path]})
    assert [patch.title for patch in await client.updates()] == ["New hero", "Balance"]
    assert (await client.balances())[0].kind == "Patch"


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "message"), [("champions", "catalogue"), ("balances", "Patch notes")])
async def test_invalid_envelope(client: MarvelRivalsClient, method: str, message: str) -> None:
    client._get = AsyncMock(return_value={"unexpected": []})
    with pytest.raises(MarvelRivalsError, match=message):
        await getattr(client, method)()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "message"),
    [(401, "credentials"), (403, "credentials"), (404, "not found"), (429, "rate limit"), (502, "HTTP 502")],
)
async def test_http_status(client: MarvelRivalsClient, status: int, message: str) -> None:
    client.session = MagicMock()
    client.session.closed = False
    client.session.get.return_value.__aenter__.return_value.status = status
    with pytest.raises(MarvelRivalsError, match=message):
        await client._get("player/75978910")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("uid", "season", "message"),
    [("MarkNo1", None, "numeric"), ("75978910", 100, "Season")],
)
async def test_invalid_args(client: MarvelRivalsClient, uid: str, season: int | None, message: str) -> None:
    with pytest.raises(MarvelRivalsError, match=message):
        await client.player(uid, season=season)


@pytest.mark.asyncio
async def test_missing_key() -> None:
    client = MarvelRivalsClient("")
    with pytest.raises(MarvelRivalsError, match="MARVEL_RIVALS_API_KEY"):
        await client.champions()
    assert client.session is None


def test_discord_contract() -> None:
    pytest.importorskip("discord.app_commands")
    from bundle.discord.cogs.marvel_rivals import MarvelRivalsCog
    from bundle.discord.embeds import EmbedFactory

    root = MarvelRivalsCog.mr
    assert {"stats", "meta", "updates", "champions", "c"} <= {cmd.name for cmd in root.commands}
    assert {"list", "stats"} <= {cmd.name for cmd in root.get_command("c").commands}

    bot = SimpleNamespace(embeds=EmbedFactory(bot_name="TheBundle"))
    embed = MarvelRivalsCog._embed(bot, PlayerStats.from_api(PLAYER, season=21))
    assert "MarkNo1" in embed.title
    assert "Season 21" in embed.description and "Mantis" in embed.description
    assert "season=21" in embed.description
    assert any(field.name == "Win rate" and field.value == "55.0%" for field in embed.fields)
