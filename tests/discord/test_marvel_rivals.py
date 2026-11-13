# Copyright 2026 HorusElohim
#
# Licensed under the Apache License, Version 2.0.
"""Marvel Rivals model and Discord integration tests."""

from __future__ import annotations

import pytest

from bundle.marvel_rivals.client import HeroStats, MarvelRivalsError, MatchStats, PlayerStats


def player_payload() -> dict:
    return {
        "uid": 75978910,
        "name": "MarkNo1",
        "player": {"level": "42", "rank": {"rank": "Diamond"}, "isPrivate": False},
        "isPrivate": False,
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
            {"hero_name": "Luna Snow", "matches": 8, "wins": 5, "kills": 60, "play_time": 900},
            {"hero_name": "Mantis", "matches": 12, "wins": 6, "kills": 30, "play_time": 1500},
        ],
    }


def test_player_stats_from_api() -> None:
    stats = PlayerStats.from_api(player_payload(), season=21)
    assert stats.name == "MarkNo1"
    assert stats.uid == 75978910
    assert stats.rank == "Diamond"
    assert stats.season == 21
    assert stats.ranked.win_rate == 55
    assert stats.ranked.kda == 2.8
    assert [hero.name for hero in stats.top_heroes] == ["Mantis", "Luna Snow"]


def test_missing_rank_and_games() -> None:
    payload = player_payload()
    payload["player"]["rank"] = None
    payload["overall_stats"]["ranked"] = {"total_matches": 0}
    payload["heroes_ranked"] = []
    stats = PlayerStats.from_api(payload)
    assert stats.rank is None
    assert stats.top_heroes == []
    assert stats.ranked.win_rate is None
    assert stats.ranked.kda is None


def test_private_profile_is_rejected() -> None:
    payload = player_payload()
    payload["isPrivate"] = True
    with pytest.raises(MarvelRivalsError, match="private"):
        PlayerStats.from_api(payload)


def test_missing_ranked_payload_is_rejected() -> None:
    payload = player_payload()
    payload["overall_stats"].pop("ranked")
    with pytest.raises(MarvelRivalsError, match="Ranked"):
        PlayerStats.from_api(payload)


def test_corrupt_numbers_are_rejected() -> None:
    payload = player_payload()
    payload["overall_stats"]["ranked"]["total_wins"] = "not-a-number"
    with pytest.raises(MarvelRivalsError, match="invalid"):
        PlayerStats.from_api(payload)


def test_win_rate_and_kda_zero_death() -> None:
    stats = MatchStats(matches=2, wins=1, kills=6, assists=4, deaths=0)
    assert stats.win_rate == 50
    assert stats.kda == 10
    assert HeroStats(name="Mantis", matches=4, wins=3).win_rate == 75


def test_discord_stats_embed() -> None:
    pytest.importorskip("discord")
    from bundle.discord.cogs.marvel_rivals import MarvelRivalsCog
    from bundle.discord.embeds import EmbedFactory

    class FakeBot:
        embeds = EmbedFactory(bot_name="TheBundle")

    embed = MarvelRivalsCog._embed(FakeBot(), PlayerStats.from_api(player_payload(), season=21))
    assert "MarkNo1" in embed.title
    assert "Season 21" in embed.description
    assert "Mantis" in embed.description
    assert "season=21" in embed.description
    assert any(field.name == "Win rate" and field.value == "55.0%" for field in embed.fields)


def test_private_profile_nested_is_rejected() -> None:
    payload = player_payload()
    payload["player"]["isPrivate"] = True
    with pytest.raises(MarvelRivalsError, match="private"):
        PlayerStats.from_api(payload)


def test_unexpected_response_is_rejected() -> None:
    with pytest.raises(MarvelRivalsError, match="unexpected"):
        PlayerStats.from_api([])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "credentials"),
        (403, "credentials"),
        (404, "No Marvel Rivals player"),
        (429, "rate limit"),
        (502, "HTTP 502"),
    ],
)
async def test_api_status_errors(status: int, message: str) -> None:
    from bundle.marvel_rivals.client import MarvelRivalsClient

    class Response:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    class Session:
        def get(self, *_args, **_kwargs):
            response = Response()
            response.status = status
            return response

    client = MarvelRivalsClient("test-key")
    await client.close()
    client.session = Session()
    with pytest.raises(MarvelRivalsError, match=message):
        await client.player("75978910", season=21)


@pytest.mark.asyncio
async def test_invalid_uid_and_season() -> None:
    from bundle.marvel_rivals.client import MarvelRivalsClient

    client = MarvelRivalsClient("test-key")
    try:
        with pytest.raises(MarvelRivalsError, match="numeric"):
            await client.player("MarkNo1")
        with pytest.raises(MarvelRivalsError, match="Season"):
            await client.player("75978910", season=100)
    finally:
        await client.close()
