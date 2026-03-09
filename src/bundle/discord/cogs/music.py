"""Music playback cog — queue-based YouTube streaming with interactive controls."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


# ---------------------------------------------------------------------------
# Per-guild state
# ---------------------------------------------------------------------------


@dataclass
class GuildState:
    """All per-guild player state.  One instance per active guild."""

    # Queue
    queue: list[YoutubeTrackData] = field(default_factory=list)
    current_index: int = -1  # index of the playing track; -1 = not started

    # Playback control flags
    skip_auto_advance: bool = False  # True → _after_track ignores the next stop signal
    waiting_for_track: bool = False  # True → at end of queue but still resolving

    # Resolution tasks (one per !play call)
    resolve_tasks: list[asyncio.Task] = field(default_factory=list)
    resolving: bool = False  # True while any resolve task is running

    # Discord objects
    now_playing_msg: discord.Message | None = None
    notify_msg: discord.Message | None = None
    text_channel: discord.TextChannel | None = None
    view: PlayerControls | None = None

    # ---------- convenience properties ----------

    @property
    def current_track(self) -> YoutubeTrackData | None:
        if 0 <= self.current_index < len(self.queue):
            return self.queue[self.current_index]
        return None

    @property
    def has_next(self) -> bool:
        return self.current_index + 1 < len(self.queue)

    @property
    def has_prev(self) -> bool:
        return self.current_index > 0

    def queue_pos_str(self) -> str:
        total = len(self.queue)
        suffix = "+" if self.resolving else ""
        return f"{self.current_index + 1} / {total}{suffix}"


# ---------------------------------------------------------------------------
# Player controls view
# ---------------------------------------------------------------------------


class PlayerControls(discord.ui.View):
    """Five-button control strip attached to the now-playing embed."""

    def __init__(self, cog: "MusicCog", guild_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    # ⏮ Previous
    @discord.ui.button(emoji="\u23EE\uFE0F", style=discord.ButtonStyle.secondary)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog._advance(interaction.guild, -1)
        await interaction.response.defer()

    # ⏯ Pause / Resume
    @discord.ui.button(emoji="\u23EF\uFE0F", style=discord.ButtonStyle.primary)
    async def btn_pause(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        vc = interaction.guild.voice_client
        state = self.cog._get_state(self.guild_id)
        if not vc or not state:
            await interaction.response.send_message("Nothing playing.", ephemeral=True)
            return
        if vc.is_paused():
            vc.resume()
            await self.cog._update_now_playing(self.guild_id, status="Playing")
        elif vc.is_playing():
            vc.pause()
            await self.cog._update_now_playing(self.guild_id, status="Paused")
        await interaction.response.defer()

    # ⏭ Skip
    @discord.ui.button(emoji="\u23ED\uFE0F", style=discord.ButtonStyle.secondary)
    async def btn_skip(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog._advance(interaction.guild, +1)
        await interaction.response.defer()

    # ⏹ Stop
    @discord.ui.button(emoji="\u23F9\uFE0F", style=discord.ButtonStyle.danger)
    async def btn_stop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog._stop_guild(interaction.guild)
        await interaction.response.defer()

    # 📋 Queue
    @discord.ui.button(emoji="\U0001F4CB", style=discord.ButtonStyle.secondary)
    async def btn_queue(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        state = self.cog._get_state(self.guild_id)
        if not state or not state.queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=self.cog._queue_embed(state),
            ephemeral=True,
        )

    def disable_all(self) -> None:
        for item in self.children:
            item.disabled = True
        super().stop()


# ---------------------------------------------------------------------------
# Music cog
# ---------------------------------------------------------------------------


class MusicCog(commands.Cog, name="music"):
    """Queue-based YouTube audio streaming."""

    def __init__(self, bot: "Bot") -> None:
        self.bot = bot
        self._states: dict[int, GuildState] = {}

    # ---------- state helpers ----------

    def _get_state(self, guild_id: int) -> GuildState | None:
        return self._states.get(guild_id)

    def _ensure_state(self, guild_id: int, text_channel: discord.TextChannel) -> GuildState:
        if guild_id not in self._states:
            self._states[guild_id] = GuildState(text_channel=text_channel)
        return self._states[guild_id]

    def _clear_state(self, guild_id: int) -> None:
        state = self._states.pop(guild_id, None)
        if state:
            for task in state.resolve_tasks:
                task.cancel()

    # ---------- embed builders ----------

    def _avatar(self) -> str:
        return self.bot.brand_avatar_url or ""

    def _now_playing_embed(self, track: YoutubeTrackData, status: str, state: GuildState) -> discord.Embed:
        return embeds.now_playing(
            title=track.title,
            author=track.author,
            duration=_fmt_duration(track.duration),
            status=status,
            queue_pos=state.queue_pos_str(),
            thumbnail_url=track.thumbnail_url or None,
            bot_avatar_url=self._avatar(),
            bot_name=self.bot.brand_name,
        )

    def _queue_embed(self, state: GuildState) -> discord.Embed:
        lines: list[str] = []
        for i, track in enumerate(state.queue):
            marker = "\u25B6" if i == state.current_index else f"{i + 1}."
            lines.append(f"`{marker}` **{track.title}** — {track.author} `{_fmt_duration(track.duration)}`")
        shown = lines[:20]
        description = "\n".join(shown)
        if len(state.queue) > 20:
            description += f"\n*... and {len(state.queue) - 20} more*"
        if state.resolving:
            description += "\n*⏳ Still resolving...*"
        return embeds.info(
            title=f"Queue — {len(state.queue)} track(s)",
            description=description or "Queue is empty.",
            bot_avatar_url=self._avatar(),
            bot_name=self.bot.brand_name,
        )

    # ---------- now-playing message ----------

    async def _update_now_playing(self, guild_id: int, *, status: str) -> None:
        state = self._get_state(guild_id)
        if not state or not state.now_playing_msg or not state.current_track:
            return
        try:
            await state.now_playing_msg.edit(
                embed=self._now_playing_embed(state.current_track, status, state),
                view=state.view,
            )
        except discord.HTTPException:
            pass

    async def _send_or_edit_now_playing(self, guild_id: int, track: YoutubeTrackData, status: str) -> None:
        """Create or update the persistent now-playing message."""
        state = self._get_state(guild_id)
        if not state:
            return
        embed = self._now_playing_embed(track, status, state)
        view = PlayerControls(self, guild_id)
        state.view = view
        if state.now_playing_msg:
            try:
                await state.now_playing_msg.edit(embed=embed, view=view)
                return
            except discord.NotFound:
                pass
        if state.text_channel:
            state.now_playing_msg = await state.text_channel.send(embed=embed, view=view)

    # ---------- core playback ----------

    async def _play_current(self, guild: discord.Guild) -> None:
        """Start playing state.queue[state.current_index] in the voice channel."""
        state = self._get_state(guild.id)
        if not state:
            return

        track = state.current_track
        if not track:
            # Queue exhausted
            if state.resolving:
                state.waiting_for_track = True
                if state.now_playing_msg:
                    try:
                        await state.now_playing_msg.edit(
                            embed=embeds.info(
                                title="Music",
                                description="Waiting for next track...",
                                bot_avatar_url=self._avatar(),
                                bot_name=self.bot.brand_name,
                            ),
                            view=state.view,
                        )
                    except discord.HTTPException:
                        pass
            else:
                # Truly finished
                if state.view:
                    state.view.disable_all()
                if state.now_playing_msg and state.queue:
                    last = state.queue[-1]
                    try:
                        await state.now_playing_msg.edit(
                            embed=self._now_playing_embed(last, "Finished", state),
                            view=state.view,
                        )
                    except discord.HTTPException:
                        pass
                self._clear_state(guild.id)
                vc = guild.voice_client
                if vc:
                    await vc.disconnect()
            return

        vc = guild.voice_client
        if not vc or not vc.is_connected():
            log.warning("Voice client missing for guild %s", guild.id)
            return

        stream_url = track.video_url or track.audio_url
        if not stream_url:
            log.warning("No stream URL for track '%s', skipping", track.title)
            state.current_index += 1
            await self._play_current(guild)
            return

        loop = asyncio.get_running_loop()
        source = discord.FFmpegPCMAudio(stream_url, before_options=FFMPEG_BEFORE_OPTIONS, options=FFMPEG_OPTIONS)
        vc.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self._after_track(guild.id, e), loop
            ),
        )
        await self._send_or_edit_now_playing(guild.id, track, "Playing")

    async def _after_track(self, guild_id: int, error: Exception | None) -> None:
        """Called (via run_coroutine_threadsafe) when a track finishes."""
        if error:
            log.error("Playback error in guild %s: %s", guild_id, error)

        state = self._get_state(guild_id)
        if not state:
            return  # stop() already cleaned up

        if state.skip_auto_advance:
            # This fire was triggered by an explicit skip/prev — do nothing;
            # the skip handler already set current_index and will call _play_current.
            state.skip_auto_advance = False
            return

        # Natural track end — advance
        state.current_index += 1
        guild = self.bot.get_guild(guild_id)
        if guild:
            await self._play_current(guild)

    # ---------- skip / prev shared logic ----------

    async def _advance(self, guild: discord.Guild, delta: int) -> None:
        """Move current_index by delta (+1 skip, -1 prev) and play the target track."""
        state = self._get_state(guild.id)
        if not state:
            return

        vc = guild.voice_client
        target = state.current_index + delta

        if target < 0:
            log.debug("Already at first track in guild %s", guild.id)
            return
        if target >= len(state.queue):
            if not state.resolving:
                log.debug("No next track in guild %s", guild.id)
            # If resolving, the resolve task will handle playback when a new track arrives
            return

        state.current_index = target
        state.skip_auto_advance = True  # prevent _after_track from double-advancing

        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()  # fires _after_track, which skips because skip_auto_advance=True
        else:
            state.skip_auto_advance = False  # nothing to stop; clear the fence

        await self._play_current(guild)

    # ---------- stop ----------

    async def _stop_guild(self, guild: discord.Guild) -> None:
        """Cancel all tasks, disconnect, disable buttons."""
        state = self._get_state(guild.id)
        if state:
            if state.view:
                state.view.disable_all()
            if state.now_playing_msg and state.current_track:
                try:
                    await state.now_playing_msg.edit(
                        embed=self._now_playing_embed(state.current_track, "Stopped", state),
                        view=state.view,
                    )
                except discord.HTTPException:
                    pass
            if state.notify_msg:
                try:
                    await state.notify_msg.delete()
                except discord.HTTPException:
                    pass

        # Clear state BEFORE stopping vc so _after_track finds nothing
        self._clear_state(guild.id)

        vc = guild.voice_client
        if vc:
            if vc.is_playing() or vc.is_paused():
                vc.stop()
            await vc.disconnect()

    # ---------- resolution ----------

    async def _resolve_and_queue(self, url: str, guild: discord.Guild, is_first_play: bool) -> None:
        """Resolve url, append tracks to the queue, and trigger playback when ready."""
        state = self._get_state(guild.id)
        if not state:
            return

        added = 0
        try:
            async for track in pytube.resolve(url, options=YoutubeResolveOptions(best=True)):
                state = self._get_state(guild.id)
                if not state:
                    return  # stop() was called mid-resolution

                if not track.is_resolved():
                    log.warning("Skipping unresolved track from %s", url)
                    continue

                state.queue.append(track)
                added += 1

                if is_first_play and added == 1:
                    # First track of first play — kick off playback
                    state.current_index = 0
                    await self._play_current(guild)
                elif state.waiting_for_track:
                    # Playback was stalled at end of previous queue — resume
                    state.waiting_for_track = False
                    state.current_index = len(state.queue) - 1
                    await self._play_current(guild)
                else:
                    # Update queue position in the now-playing embed
                    if state.current_track:
                        await self._update_now_playing(guild.id, status="Playing")

        except asyncio.CancelledError:
            return  # stop() cancelled this task; exit silently

        except Exception:
            log.exception("Resolution failed for %s", url)
            state = self._get_state(guild.id)
            if state and state.notify_msg:
                try:
                    await state.notify_msg.edit(
                        embed=embeds.error(
                            title="Music",
                            description=f"Failed to resolve `{url}`.",
                            bot_avatar_url=self._avatar(),
                            bot_name=self.bot.brand_name,
                        )
                    )
                    state.notify_msg = None
                except discord.HTTPException:
                    pass

        finally:
            state = self._get_state(guild.id)
            if not state:
                return

            # Mark this task done
            state.resolve_tasks = [t for t in state.resolve_tasks if not t.done()]
            state.resolving = bool(state.resolve_tasks)

            # Clean up the notify message
            if not state.resolving and state.notify_msg:
                try:
                    await state.notify_msg.delete()
                except discord.HTTPException:
                    pass
                state.notify_msg = None

            # If we were waiting and all resolution is done with nothing to play → finished
            if state.waiting_for_track and not state.resolving:
                state.waiting_for_track = False
                vc = guild.voice_client
                if vc:
                    await vc.disconnect()
                self._clear_state(guild.id)

            # Update embed to remove the "+" from queue_pos
            elif state.current_track:
                vc = guild.voice_client
                status = "Playing" if vc and vc.is_playing() else "Paused" if vc and vc.is_paused() else "Playing"
                await self._update_now_playing(guild.id, status=status)

    # ---------- commands ----------

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def play(self, ctx: commands.Context, url: str) -> None:
        """Add a YouTube URL (video or playlist) to the queue and start playing.

        Usage: !play <youtube-url>
        """
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(
                embed=embeds.error(
                    title="Music",
                    description="Join a voice channel first.",
                    bot_avatar_url=self._avatar(),
                    bot_name=self.bot.brand_name,
                )
            )
            return

        voice_channel = ctx.author.voice.channel
        state = self._ensure_state(ctx.guild.id, ctx.channel)

        # Connect or move voice client
        vc = ctx.guild.voice_client
        if vc and vc.is_connected():
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)
        else:
            await voice_channel.connect()

        is_first_play = not state.queue and not state.resolving

        # Send a "Resolving..." notification
        notify = await ctx.send(
            embed=embeds.progress(
                title="Music",
                status=f"{'Starting' if is_first_play else 'Adding to queue'}: `{url}` ...",
                percent=5,
                bot_avatar_url=self._avatar(),
                bot_name=self.bot.brand_name,
            )
        )

        # If an older notify_msg is still around, replace it
        if state.notify_msg:
            try:
                await state.notify_msg.delete()
            except discord.HTTPException:
                pass
        state.notify_msg = notify
        state.resolving = True

        task = asyncio.create_task(self._resolve_and_queue(url, ctx.guild, is_first_play))
        state.resolve_tasks.append(task)

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def skip(self, ctx: commands.Context) -> None:
        """Skip to the next track in the queue."""
        state = self._get_state(ctx.guild.id)
        if not state:
            await ctx.send(
                embed=embeds.error(
                    title="Music",
                    description="Nothing playing.",
                    bot_avatar_url=self._avatar(),
                    bot_name=self.bot.brand_name,
                )
            )
            return
        await self._advance(ctx.guild, +1)

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def prev(self, ctx: commands.Context) -> None:
        """Go back to the previous track."""
        state = self._get_state(ctx.guild.id)
        if not state:
            await ctx.send(
                embed=embeds.error(
                    title="Music",
                    description="Nothing playing.",
                    bot_avatar_url=self._avatar(),
                    bot_name=self.bot.brand_name,
                )
            )
            return
        await self._advance(ctx.guild, -1)

    @commands.command(name="queue")
    @tracer.Async.decorator.call_raise
    async def show_queue(self, ctx: commands.Context) -> None:
        """Display the current queue."""
        state = self._get_state(ctx.guild.id)
        if not state or not state.queue:
            await ctx.send(
                embed=embeds.error(
                    title="Music",
                    description="Queue is empty.",
                    bot_avatar_url=self._avatar(),
                    bot_name=self.bot.brand_name,
                )
            )
            return
        await ctx.send(embed=self._queue_embed(state))

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def stop(self, ctx: commands.Context) -> None:
        """Stop playback, clear the queue, and disconnect."""
        await self._stop_guild(ctx.guild)
        await ctx.send(
            embed=embeds.success(
                title="Music",
                description="Playback stopped.",
                bot_avatar_url=self._avatar(),
                bot_name=self.bot.brand_name,
            )
        )

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def pause(self, ctx: commands.Context) -> None:
        """Pause playback."""
        vc = ctx.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await self._update_now_playing(ctx.guild.id, status="Paused")

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def resume(self, ctx: commands.Context) -> None:
        """Resume paused playback."""
        vc = ctx.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await self._update_now_playing(ctx.guild.id, status="Playing")
