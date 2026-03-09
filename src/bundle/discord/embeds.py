"""Reusable Discord embed builders for the Discord bot.

Each builder returns a ``discord.Embed`` ready to be sent via ``channel.send(embed=...)``.
All embeds share a consistent style: colored sidebar, timestamp, and bot-branded footer.
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


def _footer_name(bot_name: str | None) -> str:
    return bot_name or "Discord Bot"


def _base(
    *,
    title: str,
    description: str,
    color: int,
    bot_avatar_url: str | None = None,
    bot_name: str | None = None,
) -> discord.Embed:
    """Create a timestamped embed with a branded footer."""
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
    embed.set_footer(text=_footer_name(bot_name), icon_url=bot_avatar_url)
    return embed


def online(bot_user: discord.User, guild_count: int, latency_ms: int, *, bot_name: str | None = None) -> discord.Embed:
    """Bot came online with guild count and latency."""
    avatar = bot_user.display_avatar.url
    name = _footer_name(bot_name)
    embed = _base(
        title=f"{name} Online",
        description=f"**{name}** is up and running.",
        color=Color.ONLINE,
        bot_avatar_url=avatar,
        bot_name=name,
    )
    embed.add_field(name="Guilds", value=str(guild_count), inline=True)
    embed.add_field(name="Latency", value=f"{latency_ms}ms", inline=True)
    embed.set_thumbnail(url=avatar)
    return embed


def offline(bot_user: discord.User, *, bot_name: str | None = None) -> discord.Embed:
    """Bot shutting down."""
    avatar = bot_user.display_avatar.url
    name = _footer_name(bot_name)
    return _base(
        title=f"{name} Offline",
        description=f"**{name}** is shutting down.",
        color=Color.OFFLINE,
        bot_avatar_url=avatar,
        bot_name=name,
    )


def welcome(member: discord.Member, bot_avatar_url: str | None = None, bot_name: str | None = None) -> discord.Embed:
    """New member joined with member avatar and server member count."""
    guild = member.guild
    embed = _base(
        title="New Member",
        description=f"Welcome {member.mention} to **{guild.name}**!",
        color=Color.WELCOME,
        bot_avatar_url=bot_avatar_url,
        bot_name=bot_name,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Members", value=str(guild.member_count), inline=True)
    return embed


def _progress_bar(percent: int, length: int = 10) -> str:
    """Render a text-based progress bar for embed descriptions."""
    filled = round(length * percent / 100)
    return "`" + "\u2588" * filled + "\u2591" * (length - filled) + f"` {percent}%"


def progress(
    *,
    title: str,
    status: str,
    percent: int = 0,
    fields: dict[str, str] | None = None,
    thumbnail_url: str | None = None,
    bot_avatar_url: str | None = None,
    bot_name: str | None = None,
) -> discord.Embed:
    """Generic progress embed."""
    bar = _progress_bar(min(max(percent, 0), 100))
    embed = _base(
        title=title,
        description=f"{status}\n{bar}",
        color=Color.PROGRESS,
        bot_avatar_url=bot_avatar_url,
        bot_name=bot_name,
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    for name, value in (fields or {}).items():
        embed.add_field(name=name, value=value, inline=True)
    return embed


def success(
    *,
    title: str,
    description: str,
    fields: dict[str, str] | None = None,
    thumbnail_url: str | None = None,
    bot_avatar_url: str | None = None,
    bot_name: str | None = None,
) -> discord.Embed:
    """Operation completed."""
    embed = _base(
        title=title,
        description=description,
        color=Color.SUCCESS,
        bot_avatar_url=bot_avatar_url,
        bot_name=bot_name,
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    for name, value in (fields or {}).items():
        embed.add_field(name=name, value=value, inline=True)
    return embed


def error(
    *,
    title: str,
    description: str,
    bot_avatar_url: str | None = None,
    bot_name: str | None = None,
) -> discord.Embed:
    """Operation failed."""
    return _base(
        title=title,
        description=description,
        color=Color.ERROR,
        bot_avatar_url=bot_avatar_url,
        bot_name=bot_name,
    )


def info(
    *,
    title: str,
    description: str,
    fields: dict[str, str] | None = None,
    thumbnail_url: str | None = None,
    bot_avatar_url: str | None = None,
    bot_name: str | None = None,
) -> discord.Embed:
    """Informational embed."""
    embed = _base(
        title=title,
        description=description,
        color=Color.INFO,
        bot_avatar_url=bot_avatar_url,
        bot_name=bot_name,
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    for name, value in (fields or {}).items():
        embed.add_field(name=name, value=value, inline=True)
    return embed


MUSIC = 0xE91E63  # pink


def now_playing(
    *,
    title: str,
    author: str,
    duration: str,
    status: str = "Playing",
    queue_pos: str | None = None,
    thumbnail_url: str | None = None,
    bot_avatar_url: str | None = None,
    bot_name: str | None = None,
) -> discord.Embed:
    """Now-playing embed with track info and optional queue position."""
    embed = _base(
        title=title,
        description=f"**{status}**",
        color=MUSIC,
        bot_avatar_url=bot_avatar_url,
        bot_name=bot_name,
    )
    if queue_pos:
        embed.add_field(name="Track", value=queue_pos, inline=True)
    embed.add_field(name="Author", value=author, inline=True)
    embed.add_field(name="Duration", value=duration, inline=True)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    return embed
