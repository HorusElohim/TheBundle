"""Music playback cog — join voice, stream YouTube audio with interactive controls."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bundle.core import logger, tracer
from bundle.youtube import pytube
from bundle.youtube.track import YoutubeResolveOptions, YoutubeTrackData

from .. import embeds

if TYPE_CHECKING:
    from ..bot import Bot

log = logger.get_logger(__name__)

FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS = "-vn"


def _format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


class PlayerControls(discord.ui.View):
    """Interactive play/pause/stop buttons attached to the now-playing embed."""

    def __init__(self, cog: "MusicCog", ctx: commands.Context) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.ctx = ctx

    @discord.ui.button(emoji="\u23EF\uFE0F", style=discord.ButtonStyle.primary)
    async def toggle_pause(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Toggle between pause and resume."""
        vc = self.ctx.guild.voice_client
        if not vc:
            await interaction.response.send_message("Not connected to voice.", ephemeral=True)
            return
        if vc.is_paused():
            vc.resume()
            await self.cog._update_now_playing(self.ctx, status="Playing")
        elif vc.is_playing():
            vc.pause()
            await self.cog._update_now_playing(self.ctx, status="Paused")
        await interaction.response.defer()

    @discord.ui.button(emoji="\u23F9\uFE0F", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Stop playback and disconnect."""
        vc = self.ctx.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
        state = self.cog._state.get(self.ctx.guild.id)
        self.cog._clear_state(self.ctx.guild.id)
        self.stop_view()
        embed = self.cog._now_playing_embed(state[0], "Stopped") if state else interaction.message.embeds[0]
        await interaction.response.edit_message(embed=embed, view=self)

    def stop_view(self) -> None:
        for item in self.children:
            item.disabled = True
        super().stop()


class MusicCog(commands.Cog, name="music"):
    """Stream YouTube audio to a voice channel."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        # guild_id -> (track, message, view)
        self._state: dict[int, tuple[YoutubeTrackData, discord.Message, PlayerControls]] = {}

    def _avatar(self) -> str:
        return self.bot.user.display_avatar.url

    def _clear_state(self, guild_id: int) -> None:
        self._state.pop(guild_id, None)

    def _now_playing_embed(self, track: YoutubeTrackData, status: str) -> discord.Embed:
        return embeds.now_playing(
            title=track.title,
            author=track.author,
            duration=_format_duration(track.duration),
            status=status,
            thumbnail_url=track.thumbnail_url or None,
            bot_avatar_url=self._avatar(),
        )

    async def _update_now_playing(self, ctx: commands.Context, *, status: str) -> None:
        state = self._state.get(ctx.guild.id)
        if not state:
            return
        track, msg, _ = state
        try:
            await msg.edit(embed=self._now_playing_embed(track, status))
        except discord.HTTPException:
            pass

    def _after_playback(self, ctx: commands.Context, error: Exception | None) -> None:
        if error:
            log.error(f"Playback error: {error}")
        self._clear_state(ctx.guild.id)

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def play(self, ctx: commands.Context, url: str) -> None:
        """Resolve a YouTube URL and stream audio to your voice channel.

        Usage: !play <youtube-url>
        """
        # Verify user is in a voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(
                embed=embeds.error(title="Music", description="Join a voice channel first.", bot_avatar_url=self._avatar())
            )
            return

        voice_channel = ctx.author.voice.channel

        # Send progress embed
        msg = await ctx.send(
            embed=embeds.progress(title="Music", status=f"Resolving `{url}` ...", percent=10, bot_avatar_url=self._avatar())
        )

        try:
            # Resolve
            track: YoutubeTrackData | None = None
            async for result in pytube.resolve(url, options=YoutubeResolveOptions(best=True)):
                track = result
                await msg.edit(
                    embed=embeds.progress(
                        title="Music",
                        status=f"Fetched **{track.title}**",
                        percent=50,
                        thumbnail_url=track.thumbnail_url or None,
                        bot_avatar_url=self._avatar(),
                    )
                )

            if not track or not track.video_url:
                await msg.edit(
                    embed=embeds.error(
                        title="Music", description=f"No video stream found for `{url}`.", bot_avatar_url=self._avatar()
                    )
                )
                return

            # Connect to voice
            vc = ctx.guild.voice_client
            if vc and vc.is_connected():
                if vc.channel != voice_channel:
                    await vc.move_to(voice_channel)
                if vc.is_playing():
                    vc.stop()
            else:
                vc = await voice_channel.connect()

            # Stream directly from URL — no download needed
            stream_url = track.video_url or track.audio_url
            log.info(f"Streaming from URL: {stream_url[:80]}...")
            source = discord.FFmpegPCMAudio(
                stream_url,
                before_options=FFMPEG_BEFORE_OPTIONS,
                options=FFMPEG_OPTIONS,
            )
            vc.play(source, after=lambda e: self._after_playback(ctx, e))

            # Send now-playing embed with controls
            view = PlayerControls(self, ctx)
            await msg.edit(embed=self._now_playing_embed(track, "Playing"), view=view)
            self._state[ctx.guild.id] = (track, msg, view)

        except Exception as exc:
            log.exception(f"Music play failed for {url}")
            await msg.edit(
                embed=embeds.error(title="Music Failed", description=f"```{exc}```", bot_avatar_url=self._avatar())
            )

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def stop(self, ctx: commands.Context) -> None:
        """Stop playback and disconnect from voice."""
        vc = ctx.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
        state = self._state.get(ctx.guild.id)
        self._clear_state(ctx.guild.id)
        if state:
            track, msg, view = state
            view.stop_view()
            try:
                await msg.edit(embed=self._now_playing_embed(track, "Stopped"), view=view)
            except discord.HTTPException:
                pass
        await ctx.send(
            embed=embeds.success(title="Music", description="Playback stopped.", bot_avatar_url=self._avatar())
        )
