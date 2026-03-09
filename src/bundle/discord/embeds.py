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
    PROGRESS = 0xFEE75C  # yellow
    SUCCESS = 0x57F287  # green
    ERROR = 0xED4245  # red


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


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

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
) -> discord.Embed:
    """Generic progress embed — yellow sidebar, progress bar, arbitrary fields."""
    bar = _progress_bar(min(max(percent, 0), 100))
    embed = _base(title=title, description=f"{status}\n{bar}", color=Color.PROGRESS, bot_avatar_url=bot_avatar_url)
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
) -> discord.Embed:
    """Operation completed — green embed."""
    embed = _base(title=title, description=description, color=Color.SUCCESS, bot_avatar_url=bot_avatar_url)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    for name, value in (fields or {}).items():
        embed.add_field(name=name, value=value, inline=True)
    return embed


def error(*, title: str, description: str, bot_avatar_url: str | None = None) -> discord.Embed:
    """Operation failed — red embed."""
    return _base(title=title, description=description, color=Color.ERROR, bot_avatar_url=bot_avatar_url)


# ---------------------------------------------------------------------------
# Now Playing
# ---------------------------------------------------------------------------

MUSIC = 0xE91E63  # pink


def now_playing(
    *,
    title: str,
    author: str,
    duration: str,
    status: str = "Playing",
    thumbnail_url: str | None = None,
    bot_avatar_url: str | None = None,
) -> discord.Embed:
    """Now-playing embed — pink sidebar, track info."""
    embed = _base(title=title, description=f"**{status}**", color=MUSIC, bot_avatar_url=bot_avatar_url)
    embed.add_field(name="Author", value=author, inline=True)
    embed.add_field(name="Duration", value=duration, inline=True)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    return embed
