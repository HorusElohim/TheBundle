"""Music playback cog -- queue-based YouTube streaming with interactive controls."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bundle.core import logger, tracer
from bundle.youtube import pytube
from bundle.youtube.track import YoutubeResolveOptions

from .controls import PlayerControls
from .embed import PlayerEmbed, vc_status
from .player import GuildPlayer
from .queue import TrackQueue

if TYPE_CHECKING:
    from bundle.discord.bot import Bot

log = logger.get_logger(__name__)

ALONE_TIMEOUT = 30  # seconds before auto-disconnect when alone in VC
PAUSE_TIMEOUT = 300  # seconds before auto-disconnect when paused (5 min)


@dataclass
class GuildSession:
    """Bundles the per-guild components."""

    queue: TrackQueue
    player: GuildPlayer
    embed: PlayerEmbed
    resolve_tasks: list[asyncio.Task] = field(default_factory=list)
    alone_task: asyncio.Task | None = None
    pause_task: asyncio.Task | None = None


class MusicCog(commands.Cog, name="music"):
    """Queue-based YouTube audio streaming."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._sessions: dict[int, GuildSession] = {}

    # ---- session management ----

    def _get_session(self, guild_id: int) -> GuildSession | None:
        return self._sessions.get(guild_id)

    def _ensure_session(self, guild_id: int, text_channel: discord.TextChannel) -> GuildSession:
        if guild_id not in self._sessions:
            queue = TrackQueue()
            player = GuildPlayer(on_track_end=self._on_track_end)
            embed = PlayerEmbed(self.bot.embeds, queue, player, text_channel)
            self._sessions[guild_id] = GuildSession(queue=queue, player=player, embed=embed)
        return self._sessions[guild_id]

    def _clear_session(self, guild_id: int) -> None:
        gs = self._sessions.pop(guild_id, None)
        if gs:
            for task in gs.resolve_tasks:
                task.cancel()
            if gs.alone_task and not gs.alone_task.done():
                gs.alone_task.cancel()
            if gs.pause_task and not gs.pause_task.done():
                gs.pause_task.cancel()
            gs.embed.cancel_seek_loop()

    # ---- core playback ----

    async def _play_current(self, guild: discord.Guild) -> None:
        gs = self._get_session(guild.id)
        if not gs:
            return

        track = gs.queue.current

        if not track:
            if gs.queue.resolving:
                gs.queue.waiting = True
                await gs.embed.send_or_update(
                    self.bot.embeds.info(title="Music", description="\u23F3 Waiting for next track..."),
                    gs.embed.view,
                )
            else:
                await gs.embed.show_finished()
                self._clear_session(guild.id)
                vc = guild.voice_client
                if vc:
                    await vc.disconnect()
            return

        vc = guild.voice_client
        if not vc or not vc.is_connected():
            log.warning("Voice client missing for guild %s", guild.id)
            return

        if not gs.player.play(vc, track, guild.id):
            gs.queue.advance()
            await self._play_current(guild)
            return

        self._cancel_pause_timer(guild.id)
        view = PlayerControls(self, guild.id)
        gs.embed.view = view
        await gs.embed.send_or_update(gs.embed.now_playing(track, "Playing"), view)
        gs.embed.start_seek_loop(guild)

    async def _on_track_end(self, guild_id: int, error: Exception | None) -> None:
        gs = self._get_session(guild_id)
        if not gs:
            return
        gs.queue.advance()
        guild = self.bot.get_guild(guild_id)
        if guild:
            await self._play_current(guild)

    # ---- skip / prev ----

    async def _advance(self, guild: discord.Guild, delta: int) -> None:
        gs = self._get_session(guild.id)
        if not gs:
            return

        target = gs.queue.index + delta
        if target < 0 or target >= len(gs.queue):
            return

        gs.queue.index = target
        vc = guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            gs.player.stop(vc)

        await self._play_current(guild)

    # ---- stop ----

    async def _stop_guild(self, guild: discord.Guild) -> None:
        gs = self._get_session(guild.id)
        vc = guild.voice_client

        if gs:
            await gs.embed.show_stopped()
            if vc:
                gs.player.stop(vc)
            self._clear_session(guild.id)

        if vc:
            await vc.disconnect()

    # ---- pause / resume (centralized for timer management) ----

    async def _pause_guild(self, guild: discord.Guild) -> bool:
        gs = self._get_session(guild.id)
        vc = guild.voice_client
        if not gs or not vc:
            return False
        if gs.player.pause(vc):
            await gs.embed.refresh(status="Paused")
            self._start_pause_timer(guild.id)
            return True
        return False

    async def _resume_guild(self, guild: discord.Guild) -> bool:
        gs = self._get_session(guild.id)
        vc = guild.voice_client
        if not gs or not vc:
            return False
        if gs.player.resume(vc):
            await gs.embed.refresh(status="Playing")
            self._cancel_pause_timer(guild.id)
            return True
        return False

    # ---- voice lifecycle timers ----

    def _start_alone_timer(self, guild_id: int) -> None:
        gs = self._get_session(guild_id)
        if not gs:
            return
        self._cancel_alone_timer(guild_id)
        gs.alone_task = asyncio.create_task(self._alone_timeout(guild_id))

    def _cancel_alone_timer(self, guild_id: int) -> None:
        gs = self._get_session(guild_id)
        if gs and gs.alone_task and not gs.alone_task.done():
            gs.alone_task.cancel()
            gs.alone_task = None

    def _start_pause_timer(self, guild_id: int) -> None:
        gs = self._get_session(guild_id)
        if not gs:
            return
        self._cancel_pause_timer(guild_id)
        gs.pause_task = asyncio.create_task(self._pause_timeout(guild_id))

    def _cancel_pause_timer(self, guild_id: int) -> None:
        gs = self._get_session(guild_id)
        if gs and gs.pause_task and not gs.pause_task.done():
            gs.pause_task.cancel()
            gs.pause_task = None

    async def _alone_timeout(self, guild_id: int) -> None:
        try:
            await asyncio.sleep(ALONE_TIMEOUT)
        except asyncio.CancelledError:
            return
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        log.info("Auto-disconnecting from guild %s (alone in VC)", guild_id)
        gs = self._get_session(guild_id)
        if gs:
            await gs.embed.show_idle_disconnect("Disconnected \u2014 alone in voice channel.")
        await self._stop_guild(guild)

    async def _pause_timeout(self, guild_id: int) -> None:
        try:
            await asyncio.sleep(PAUSE_TIMEOUT)
        except asyncio.CancelledError:
            return
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        log.info("Auto-disconnecting from guild %s (paused too long)", guild_id)
        gs = self._get_session(guild_id)
        if gs:
            await gs.embed.show_idle_disconnect("Disconnected \u2014 paused for too long.")
        await self._stop_guild(guild)

    # ---- voice state listener ----

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        guild = member.guild
        gs = self._get_session(guild.id)
        if not gs:
            return

        vc = guild.voice_client
        if not vc or not vc.channel:
            return

        # Bot was force-disconnected
        if member.id == self.bot.user.id and before.channel and not after.channel:
            log.info("Bot force-disconnected from guild %s", guild.id)
            await gs.embed.show_idle_disconnect("Disconnected from voice.")
            self._clear_session(guild.id)
            return

        # Check if bot is alone in its voice channel
        humans = [m for m in vc.channel.members if not m.bot]
        if not humans:
            self._start_alone_timer(guild.id)
        else:
            self._cancel_alone_timer(guild.id)

    # ---- resolution ----

    async def _resolve_and_queue(self, url: str, guild: discord.Guild, is_first_play: bool) -> None:
        gs = self._get_session(guild.id)
        if not gs:
            return

        added = 0

        try:
            async for track in pytube.resolve(url, options=YoutubeResolveOptions(best=True)):
                gs = self._get_session(guild.id)
                if not gs:
                    return

                if not track.is_resolved():
                    log.warning("Skipping unresolved track from %s", url)
                    continue

                gs.queue.enqueue(track)
                added += 1

                if is_first_play and added == 1:
                    gs.queue.index = 0
                    await self._play_current(guild)
                elif gs.queue.waiting:
                    gs.queue.waiting = False
                    gs.queue.index = len(gs.queue) - 1
                    await self._play_current(guild)
                else:
                    if gs.queue.current:
                        await gs.embed.refresh(status=vc_status(guild.voice_client))

        except asyncio.CancelledError:
            return

        except Exception:
            log.exception("Resolution failed for %s", url)
            gs = self._get_session(guild.id)
            if gs:
                await gs.embed.show_error(f"Failed to resolve `{url}`.")

        finally:
            gs = self._get_session(guild.id)
            if not gs:
                return

            gs.resolve_tasks = [t for t in gs.resolve_tasks if not t.done()]
            gs.queue.resolving = bool(gs.resolve_tasks)

            if gs.queue.waiting and not gs.queue.resolving:
                gs.queue.waiting = False
                vc = guild.voice_client
                if vc:
                    await vc.disconnect()
                self._clear_session(guild.id)

            elif gs.queue.current:
                await gs.embed.refresh(status=vc_status(guild.voice_client))

    # ---- commands ----

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
        gs = self._ensure_session(ctx.guild.id, ctx.channel)

        vc = ctx.guild.voice_client
        if vc and vc.is_connected():
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)
        else:
            await voice_channel.connect()

        is_first_play = not gs.queue and not gs.queue.resolving
        gs.queue.resolving = True

        await gs.embed.send_or_update(
            e.progress(
                title="Music",
                status=f"{'Resolving' if is_first_play else 'Adding to queue'}: `{url}` ...",
                percent=5,
            ),
        )

        task = asyncio.create_task(self._resolve_and_queue(url, ctx.guild, is_first_play))
        gs.resolve_tasks.append(task)

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def skip(self, ctx: commands.Context) -> None:
        """Skip to the next track in the queue."""
        if not self._get_session(ctx.guild.id):
            await ctx.send(embed=self.bot.embeds.error(title="Music", description="Nothing playing."))
            return
        await self._advance(ctx.guild, +1)

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def prev(self, ctx: commands.Context) -> None:
        """Go back to the previous track."""
        if not self._get_session(ctx.guild.id):
            await ctx.send(embed=self.bot.embeds.error(title="Music", description="Nothing playing."))
            return
        await self._advance(ctx.guild, -1)

    @commands.command(name="queue")
    @tracer.Async.decorator.call_raise
    async def show_queue(self, ctx: commands.Context) -> None:
        """Display the current queue."""
        gs = self._get_session(ctx.guild.id)
        if not gs or not gs.queue:
            await ctx.send(embed=self.bot.embeds.error(title="Music", description="Queue is empty."))
            return
        await ctx.send(embed=gs.embed.queue_embed())

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
        await self._pause_guild(ctx.guild)

    @commands.command()
    @tracer.Async.decorator.call_raise
    async def resume(self, ctx: commands.Context) -> None:
        """Resume paused playback."""
        await self._resume_guild(ctx.guild)
