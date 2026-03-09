"""Music playback cog — queue-based YouTube streaming with interactive controls."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bundle.core import logger, tracer
from bundle.youtube import pytube
from bundle.youtube.track import YoutubeResolveOptions, YoutubeTrackData

if TYPE_CHECKING:
    from ..bot import Bot

log = logger.get_logger(__name__)

FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel warning"
FFMPEG_OPTIONS = "-vn"
SEEK_UPDATE_INTERVAL = 5  # seconds between seek-bar refreshes (Discord rate-limit safe)


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
    current_index: int = -1

    # Playback timing
    play_started_at: float = 0.0  # monotonic time when current track started
    pause_offset: float = 0.0  # accumulated pause duration
    paused_at: float | None = None  # monotonic time when paused (None = not paused)

    # Control flags
    skip_auto_advance: bool = False
    waiting_for_track: bool = False

    # Resolution
    resolve_tasks: list[asyncio.Task] = field(default_factory=list)
    resolving: bool = False

    # Discord objects
    msg: discord.Message | None = None  # single persistent message
    text_channel: discord.TextChannel | None = None
    view: PlayerControls | None = None
    seek_task: asyncio.Task | None = None  # periodic seek-bar updater

    # ---------- convenience ----------

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

    def elapsed_secs(self) -> int:
        if self.play_started_at == 0:
            return 0
        if self.paused_at is not None:
            return int(self.paused_at - self.play_started_at - self.pause_offset)
        return int(time.monotonic() - self.play_started_at - self.pause_offset)



# ---------------------------------------------------------------------------
# Player controls view
# ---------------------------------------------------------------------------


class PlayerControls(discord.ui.View):
    """Five-button control strip attached to the now-playing embed."""

    def __init__(self, cog: MusicCog, guild_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(emoji="\u23EE\uFE0F", style=discord.ButtonStyle.secondary)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog._advance(interaction.guild, -1)
        await interaction.response.defer()

    @discord.ui.button(emoji="\u23EF\uFE0F", style=discord.ButtonStyle.primary)
    async def btn_pause(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        vc = interaction.guild.voice_client
        state = self.cog._get_state(self.guild_id)
        if not vc or not state:
            await interaction.response.send_message("Nothing playing.", ephemeral=True)
            return
        if vc.is_paused():
            vc.resume()
            state.pause_offset += time.monotonic() - (state.paused_at or time.monotonic())
            state.paused_at = None
            await self.cog._refresh_msg(self.guild_id, status="Playing")
        elif vc.is_playing():
            vc.pause()
            state.paused_at = time.monotonic()
            await self.cog._refresh_msg(self.guild_id, status="Paused")
        await interaction.response.defer()

    @discord.ui.button(emoji="\u23ED\uFE0F", style=discord.ButtonStyle.secondary)
    async def btn_skip(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog._advance(interaction.guild, +1)
        await interaction.response.defer()

    @discord.ui.button(emoji="\u23F9\uFE0F", style=discord.ButtonStyle.danger)
    async def btn_stop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog._stop_guild(interaction.guild)
        await interaction.response.defer()

    @discord.ui.button(emoji="\U0001F4CB", style=discord.ButtonStyle.secondary)
    async def btn_queue(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        state = self.cog._get_state(self.guild_id)
        if not state or not state.queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        await interaction.response.send_message(embed=self.cog._queue_embed(state), ephemeral=True)

    def disable_all(self) -> None:
        for item in self.children:
            item.disabled = True
        super().stop()


# ---------------------------------------------------------------------------
# Music cog
# ---------------------------------------------------------------------------


class MusicCog(commands.Cog, name="music"):
    """Queue-based YouTube audio streaming."""

    def __init__(self, bot: Bot) -> None:
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
            if state.seek_task and not state.seek_task.done():
                state.seek_task.cancel()

    # ---------- embed helpers ----------

    def _now_playing_embed(self, track: YoutubeTrackData, status: str, state: GuildState) -> discord.Embed:
        return self.bot.embeds.now_playing(
            title=track.title,
            author=track.author,
            duration_secs=track.duration,
            elapsed_secs=state.elapsed_secs(),
            status=status,
            queue_pos=state.queue_pos_str(),
            thumbnail_url=track.thumbnail_url or None,
        )

    def _queue_embed(self, state: GuildState) -> discord.Embed:
        lines: list[str] = []
        for i, track in enumerate(state.queue):
            marker = "\u25B6" if i == state.current_index else f"{i + 1}."
            lines.append(f"`{marker}` **{track.title}** \u2014 {track.author} `{_fmt_duration(track.duration)}`")
        shown = lines[:20]
        description = "\n".join(shown)
        if len(state.queue) > 20:
            description += f"\n*... and {len(state.queue) - 20} more*"
        if state.resolving:
            description += "\n*\u23F3 Still resolving...*"
        return self.bot.embeds.info(
            title=f"Queue \u2014 {len(state.queue)} track(s)",
            description=description or "Queue is empty.",
        )

    # ---------- single persistent message ----------

    async def _refresh_msg(self, guild_id: int, *, status: str) -> None:
        """Update the persistent message with current track state."""
        state = self._get_state(guild_id)
        if not state or not state.msg or not state.current_track:
            return
        try:
            await state.msg.edit(
                embed=self._now_playing_embed(state.current_track, status, state),
                view=state.view,
            )
        except discord.HTTPException:
            pass

    async def _send_or_update_msg(self, guild_id: int, embed: discord.Embed, view: discord.ui.View | None = None) -> None:
        """Send a new message or edit the existing one."""
        state = self._get_state(guild_id)
        if not state:
            return
        if state.msg:
            try:
                await state.msg.edit(embed=embed, view=view)
                return
            except discord.NotFound:
                state.msg = None
        if state.text_channel:
            state.msg = await state.text_channel.send(embed=embed, view=view)

    # ---------- seek bar updater ----------

    async def _seek_loop(self, guild_id: int) -> None:
        """Periodically refresh the now-playing embed to update the seek bar."""
        try:
            while True:
                await asyncio.sleep(SEEK_UPDATE_INTERVAL)
                state = self._get_state(guild_id)
                if not state or not state.current_track:
                    return
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    return
                vc = guild.voice_client
                if not vc or not vc.is_playing():
                    continue  # paused — don't update (seek doesn't move)
                await self._refresh_msg(guild_id, status="Playing")
        except asyncio.CancelledError:
            return

    def _start_seek_loop(self, guild_id: int) -> None:
        state = self._get_state(guild_id)
        if not state:
            return
        if state.seek_task and not state.seek_task.done():
            state.seek_task.cancel()
        state.seek_task = asyncio.create_task(self._seek_loop(guild_id))

    # ---------- core playback ----------

    async def _play_current(self, guild: discord.Guild) -> None:
        """Start playing state.queue[state.current_index] in the voice channel."""
        state = self._get_state(guild.id)
        if not state:
            return

        e = self.bot.embeds
        track = state.current_track
        if not track:
            if state.resolving:
                state.waiting_for_track = True
                await self._send_or_update_msg(
                    guild.id,
                    e.info(title="Music", description="\u23F3 Waiting for next track..."),
                    state.view,
                )
            else:
                if state.view:
                    state.view.disable_all()
                if state.msg and state.queue:
                    last = state.queue[-1]
                    try:
                        await state.msg.edit(
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

        # Reset timing
        state.play_started_at = time.monotonic()
        state.pause_offset = 0.0
        state.paused_at = None

        loop = asyncio.get_running_loop()
        source = discord.FFmpegPCMAudio(stream_url, before_options=FFMPEG_BEFORE_OPTIONS, options=FFMPEG_OPTIONS)
        vc.play(
            source,
            after=lambda err: asyncio.run_coroutine_threadsafe(
                self._after_track(guild.id, err), loop
            ),
        )

        # Update the single persistent message with now-playing + controls
        view = PlayerControls(self, guild.id)
        state.view = view
        await self._send_or_update_msg(
            guild.id,
            self._now_playing_embed(track, "Playing", state),
            view,
        )
        self._start_seek_loop(guild.id)

    async def _after_track(self, guild_id: int, error: Exception | None) -> None:
        if error:
            log.error("Playback error in guild %s: %s", guild_id, error)

        state = self._get_state(guild_id)
        if not state:
            return

        if state.skip_auto_advance:
            state.skip_auto_advance = False
            return

        state.current_index += 1
        guild = self.bot.get_guild(guild_id)
        if guild:
            await self._play_current(guild)

    # ---------- skip / prev ----------

    async def _advance(self, guild: discord.Guild, delta: int) -> None:
        state = self._get_state(guild.id)
        if not state:
            return

        vc = guild.voice_client
        target = state.current_index + delta

        if target < 0:
            return
        if target >= len(state.queue):
            return

        state.current_index = target
        state.skip_auto_advance = True

        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
        else:
            state.skip_auto_advance = False

        await self._play_current(guild)

    # ---------- stop ----------

    async def _stop_guild(self, guild: discord.Guild) -> None:
        state = self._get_state(guild.id)
        if state:
            if state.view:
                state.view.disable_all()
            if state.msg and state.current_track:
                try:
                    await state.msg.edit(
                        embed=self._now_playing_embed(state.current_track, "Stopped", state),
                        view=state.view,
                    )
                except discord.HTTPException:
                    pass

        self._clear_state(guild.id)

        vc = guild.voice_client
        if vc:
            if vc.is_playing() or vc.is_paused():
                vc.stop()
            await vc.disconnect()

    # ---------- resolution ----------

    async def _resolve_and_queue(self, url: str, guild: discord.Guild, is_first_play: bool) -> None:
        state = self._get_state(guild.id)
        if not state:
            return

        e = self.bot.embeds
        added = 0
        try:
            async for track in pytube.resolve(url, options=YoutubeResolveOptions(best=True)):
                state = self._get_state(guild.id)
                if not state:
                    return

                if not track.is_resolved():
                    log.warning("Skipping unresolved track from %s", url)
                    continue

                state.queue.append(track)
                added += 1

                if is_first_play and added == 1:
                    state.current_index = 0
                    await self._play_current(guild)
                elif state.waiting_for_track:
                    state.waiting_for_track = False
                    state.current_index = len(state.queue) - 1
                    await self._play_current(guild)
                else:
                    # Refresh to update queue position / resolving count
                    if state.current_track:
                        vc = guild.voice_client
                        status = "Paused" if vc and vc.is_paused() else "Playing"
                        await self._refresh_msg(guild.id, status=status)

        except asyncio.CancelledError:
            return

        except Exception:
            log.exception("Resolution failed for %s", url)
            state = self._get_state(guild.id)
            if state and state.msg:
                try:
                    await state.msg.edit(
                        embed=e.error(title="Music", description=f"Failed to resolve `{url}`."),
                        view=state.view,
                    )
                except discord.HTTPException:
                    pass

        finally:
            state = self._get_state(guild.id)
            if not state:
                return

            state.resolve_tasks = [t for t in state.resolve_tasks if not t.done()]
            state.resolving = bool(state.resolve_tasks)

            if state.waiting_for_track and not state.resolving:
                state.waiting_for_track = False
                vc = guild.voice_client
                if vc:
                    await vc.disconnect()
                self._clear_state(guild.id)

            elif state.current_track:
                vc = guild.voice_client
                status = "Paused" if vc and vc.is_paused() else "Playing"
                await self._refresh_msg(guild.id, status=status)

    # ---------- commands ----------

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def play(self, ctx: commands.Context, url: str) -> None:
        """Add a YouTube URL (video or playlist) to the queue and start playing.

        Usage: !play <youtube-url>
        """
        e = self.bot.embeds
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(embed=e.error(title="Music", description="Join a voice channel first."))
            return

        voice_channel = ctx.author.voice.channel
        state = self._ensure_state(ctx.guild.id, ctx.channel)

        vc = ctx.guild.voice_client
        if vc and vc.is_connected():
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)
        else:
            await voice_channel.connect()

        is_first_play = not state.queue and not state.resolving
        state.resolving = True

        # Use the single persistent message for resolve progress too
        await self._send_or_update_msg(
            ctx.guild.id,
            e.progress(
                title="Music",
                status=f"{'Resolving' if is_first_play else 'Adding to queue'}: `{url}` ...",
                percent=5,
            ),
        )

        task = asyncio.create_task(self._resolve_and_queue(url, ctx.guild, is_first_play))
        state.resolve_tasks.append(task)

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def skip(self, ctx: commands.Context) -> None:
        """Skip to the next track in the queue."""
        state = self._get_state(ctx.guild.id)
        if not state:
            await ctx.send(embed=self.bot.embeds.error(title="Music", description="Nothing playing."))
            return
        await self._advance(ctx.guild, +1)

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def prev(self, ctx: commands.Context) -> None:
        """Go back to the previous track."""
        state = self._get_state(ctx.guild.id)
        if not state:
            await ctx.send(embed=self.bot.embeds.error(title="Music", description="Nothing playing."))
            return
        await self._advance(ctx.guild, -1)

    @commands.command(name="queue")
    @tracer.Async.decorator.call_raise
    async def show_queue(self, ctx: commands.Context) -> None:
        """Display the current queue."""
        state = self._get_state(ctx.guild.id)
        if not state or not state.queue:
            await ctx.send(embed=self.bot.embeds.error(title="Music", description="Queue is empty."))
            return
        await ctx.send(embed=self._queue_embed(state))

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def stop(self, ctx: commands.Context) -> None:
        """Stop playback, clear the queue, and disconnect."""
        await self._stop_guild(ctx.guild)
        await ctx.send(embed=self.bot.embeds.success(title="Music", description="Playback stopped."))

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def pause(self, ctx: commands.Context) -> None:
        """Pause playback."""
        vc = ctx.guild.voice_client
        state = self._get_state(ctx.guild.id)
        if vc and vc.is_playing() and state:
            vc.pause()
            state.paused_at = time.monotonic()
            await self._refresh_msg(ctx.guild.id, status="Paused")

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def resume(self, ctx: commands.Context) -> None:
        """Resume paused playback."""
        vc = ctx.guild.voice_client
        state = self._get_state(ctx.guild.id)
        if vc and vc.is_paused() and state:
            vc.resume()
            state.pause_offset += time.monotonic() - (state.paused_at or time.monotonic())
            state.paused_at = None
            await self._refresh_msg(ctx.guild.id, status="Playing")
