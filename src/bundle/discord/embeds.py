# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Reusable Discord embed builders for the Discord bot.

``EmbedFactory`` holds the bot brand context (name + avatar) so callers
don't have to pass ``bot_name`` / ``bot_avatar_url`` on every call.

Standalone module-level functions are kept as thin convenience wrappers.
"""

from __future__ import annotations

from datetime import datetime, timezone

import discord


class Color:
    """Discord embed sidebar colors."""

    ONLINE = 0x57F287  # green
    OFFLINE = 0xED4245  # red
    WELCOME = 0x5865F2  # blurple
    INFO = 0x3498DB  # blue
    PROGRESS = 0xFEE75C  # yellow
    SUCCESS = 0x57F287  # green
    ERROR = 0xED4245  # red
    MUSIC = 0x00FF00  # green


def _progress_bar(percent: int, length: int = 10) -> str:
    filled = round(length * percent / 100)
    return "`" + "\u2588" * filled + "\u2591" * (length - filled) + f"` {percent}%"


def _fmt_ts(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def _seek_bar(elapsed: int, total: int, length: int = 16) -> str:
    """Render a seek bar like: `0:42 ▶ ━━━━━●━━━━━━━━━━ 3:21`."""
    if total <= 0:
        return ""
    elapsed = min(elapsed, total)
    pos = elapsed / total
    dot = round(pos * (length - 1))
    bar = "\u2501" * dot + "\u25cf" + "\u2501" * (length - 1 - dot)
    return f"`{_fmt_ts(elapsed)}` {bar} `{_fmt_ts(total)}`"


class EmbedFactory:
    """Brand-aware embed builder.  Create one per bot and reuse everywhere."""

    def __init__(self, bot_name: str = "Discord Bot", bot_avatar_url: str = "") -> None:
        self.bot_name = bot_name
        self.bot_avatar_url = bot_avatar_url

    # ---- internal helpers ----

    def _base(self, *, title: str, description: str, color: int) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=self.bot_name, icon_url=self.bot_avatar_url or None)
        return embed

    def _with_extras(
        self,
        embed: discord.Embed,
        *,
        fields: dict[str, str] | None = None,
        thumbnail_url: str | None = None,
    ) -> discord.Embed:
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        for name, value in (fields or {}).items():
            embed.add_field(name=name, value=value, inline=True)
        return embed

    # ---- public builders ----

    def online(self, bot_user: discord.User, guild_count: int, latency_ms: int) -> discord.Embed:
        avatar = bot_user.display_avatar.url
        embed = self._base(
            title=f"{self.bot_name} Online",
            description=f"**{self.bot_name}** is up and running.",
            color=Color.ONLINE,
        )
        embed.add_field(name="Guilds", value=str(guild_count), inline=True)
        embed.add_field(name="Latency", value=f"{latency_ms}ms", inline=True)
        embed.set_thumbnail(url=avatar)
        return embed

    def offline(self) -> discord.Embed:
        return self._base(
            title=f"{self.bot_name} Offline",
            description=f"**{self.bot_name}** is shutting down.",
            color=Color.OFFLINE,
        )

    def welcome(self, member: discord.Member) -> discord.Embed:
        guild = member.guild
        embed = self._base(
            title="New Member",
            description=f"Welcome {member.mention} to **{guild.name}**!",
            color=Color.WELCOME,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)
        return embed

    def progress(
        self,
        *,
        title: str,
        status: str,
        percent: int = 0,
        fields: dict[str, str] | None = None,
        thumbnail_url: str | None = None,
    ) -> discord.Embed:
        bar = _progress_bar(min(max(percent, 0), 100))
        embed = self._base(title=title, description=f"{status}\n{bar}", color=Color.PROGRESS)
        return self._with_extras(embed, fields=fields, thumbnail_url=thumbnail_url)

    def success(
        self,
        *,
        title: str,
        description: str,
        fields: dict[str, str] | None = None,
        thumbnail_url: str | None = None,
    ) -> discord.Embed:
        embed = self._base(title=title, description=description, color=Color.SUCCESS)
        return self._with_extras(embed, fields=fields, thumbnail_url=thumbnail_url)

    def error(self, *, title: str, description: str) -> discord.Embed:
        return self._base(title=title, description=description, color=Color.ERROR)

    def info(
        self,
        *,
        title: str,
        description: str,
        fields: dict[str, str] | None = None,
        thumbnail_url: str | None = None,
    ) -> discord.Embed:
        embed = self._base(title=title, description=description, color=Color.INFO)
        return self._with_extras(embed, fields=fields, thumbnail_url=thumbnail_url)

    def now_playing(
        self,
        *,
        title: str,
        author: str,
        duration_secs: int,
        elapsed_secs: int = 0,
        status: str = "Playing",
        queue_pos: str | None = None,
        thumbnail_url: str | None = None,
    ) -> discord.Embed:
        # Status icon
        icons = {
            "Playing": "\u25b6",
            "Paused": "\u23f8",
            "Stopped": "\u23f9",
            "Finished": "\u2705",
        }
        icon = icons.get(status, "\u25b6")
        seek = _seek_bar(elapsed_secs, duration_secs)
        desc = f"{icon} **{status}**\n{seek}" if seek else f"{icon} **{status}**"
        embed = self._base(title=title, description=desc, color=Color.MUSIC)
        embed.add_field(name="Author", value=author, inline=True)
        if queue_pos:
            embed.add_field(name="Track", value=queue_pos, inline=True)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        return embed
