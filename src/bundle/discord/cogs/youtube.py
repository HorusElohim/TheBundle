"""YouTube resolution commands — resolve audio/video stream URLs from YouTube links."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from bundle.core import logger, tracer
from bundle.youtube import pytube
from bundle.youtube.track import YoutubeResolveOptions, YoutubeTrackData

from .. import embeds

if TYPE_CHECKING:
    from ..bot import Bot

log = logger.get_logger(__name__)


def _format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def _stream_table(track: YoutubeTrackData) -> str:
    """Build a compact markdown table of available streams."""
    lines: list[str] = []
    if track.video_streams:
        lines.append("**Video**")
        for s in track.video_streams[:5]:
            size = f"{s.filesize / 1024 / 1024:.1f}MB" if s.filesize else "?"
            lines.append(f"`{s.resolution}` {s.fps}fps {s.mime_type} {size}")
    if track.audio_streams:
        lines.append("**Audio**")
        for s in track.audio_streams[:5]:
            size = f"{s.filesize / 1024 / 1024:.1f}MB" if s.filesize else "?"
            lines.append(f"`{s.abr}` {s.mime_type} {size}")
    return "\n".join(lines) or "No streams found"


class YoutubeCog(commands.Cog, name="youtube"):
    """Resolve YouTube audio/video stream URLs."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    def _avatar(self) -> str:
        return self.bot.brand_avatar_url or ""

    @commands.command(name="yt")
    @tracer.Async.decorator.call_raise
    async def resolve(self, ctx: commands.Context, url: str) -> None:
        """Resolve a YouTube URL and show available streams.

        Usage: !yt <youtube-url>
        """
        # Send initial progress embed
        msg = await ctx.send(
            embed=embeds.progress(
                title="YouTube Resolve",
                status=f"Resolving `{url}` ...",
                percent=10,
                bot_avatar_url=self._avatar(),
                bot_name=self.bot.brand_name,
            )
        )

        try:
            options = YoutubeResolveOptions(best=True)
            track: YoutubeTrackData | None = None

            async for result in pytube.resolve(url, options=options):
                track = result
                # Update progress after metadata is fetched
                await msg.edit(
                    embed=embeds.progress(
                        title="YouTube Resolve",
                        status=f"Fetched **{track.title}**\nCollecting streams...",
                        percent=60,
                        thumbnail_url=track.thumbnail_url or None,
                        bot_avatar_url=self._avatar(),
                        bot_name=self.bot.brand_name,
                    )
                )

            if not track or not track.is_resolved():
                await msg.edit(
                    embed=embeds.error(
                        title="YouTube Resolve",
                        description=f"Could not resolve streams for `{url}`.",
                        bot_avatar_url=self._avatar(),
                        bot_name=self.bot.brand_name,
                    )
                )
                return

            fields = {
                "Author": track.author,
                "Duration": _format_duration(track.duration),
            }
            if track.video_streams:
                best = track.video_streams[0]
                fields["Best Video"] = f"`{best.resolution}` {best.fps}fps {best.mime_type}"
            if track.audio_streams:
                best = track.audio_streams[0]
                fields["Best Audio"] = f"`{best.abr}` {best.mime_type}"

            await msg.edit(
                embed=embeds.success(
                    title=track.title,
                    description=_stream_table(track),
                    fields=fields,
                    thumbnail_url=track.thumbnail_url or None,
                    bot_avatar_url=self._avatar(),
                    bot_name=self.bot.brand_name,
                )
            )

        except Exception as exc:
            log.exception(f"YouTube resolve failed for {url}")
            await msg.edit(
                embed=embeds.error(
                    title="YouTube Resolve Failed",
                    description=f"```{exc}```",
                    bot_avatar_url=self._avatar(),
                    bot_name=self.bot.brand_name,
                )
            )
