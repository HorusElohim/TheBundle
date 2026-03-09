"""Reusable Discord embed builders for TheBundle bot.

Each builder returns a ``discord.Embed`` ready to be sent via ``channel.send(embed=...)``.
All embeds share a consistent style: colored sidebar, timestamp, and bot-branded footer.
"""

from __future__ import annotations

from datetime import datetime, timezone

import discord

from . import BOT_NAME


class Color:
    """Discord embed sidebar colors."""

    ONLINE = 0x57F287  # green
    OFFLINE = 0xED4245  # red
    WELCOME = 0x5865F2  # blurple
    INFO = 0x3498DB  # blue


def _base(*, title: str, description: str, color: int, bot_avatar_url: str | None = None) -> discord.Embed:
    """Create a timestamped embed with a branded footer."""
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
    embed.set_footer(text=BOT_NAME, icon_url=bot_avatar_url)
    return embed


def online(bot_user: discord.User, guild_count: int, latency_ms: int) -> discord.Embed:
    """Bot came online — green embed with guild count and latency."""
    avatar = bot_user.display_avatar.url
    embed = _base(
        title=f"{BOT_NAME} Online",
        description=f"**{BOT_NAME}** is up and running.",
        color=Color.ONLINE,
        bot_avatar_url=avatar,
    )
    embed.add_field(name="Guilds", value=str(guild_count), inline=True)
    embed.add_field(name="Latency", value=f"{latency_ms}ms", inline=True)
    embed.set_thumbnail(url=avatar)
    return embed


def offline(bot_user: discord.User) -> discord.Embed:
    """Bot shutting down — red embed."""
    avatar = bot_user.display_avatar.url
    return _base(
        title=f"{BOT_NAME} Offline",
        description=f"**{BOT_NAME}** is shutting down.",
        color=Color.OFFLINE,
        bot_avatar_url=avatar,
    )


def welcome(member: discord.Member, bot_avatar_url: str | None = None) -> discord.Embed:
    """New member joined — blurple embed with member avatar and server member count."""
    guild = member.guild
    embed = _base(
        title="New Member",
        description=f"Welcome {member.mention} to **{guild.name}**!",
        color=Color.WELCOME,
        bot_avatar_url=bot_avatar_url,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Members", value=str(guild.member_count), inline=True)
    return embed
