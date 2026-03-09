"""Player embed -- message lifecycle and seek-bar updates."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord

from bundle.youtube.track import YoutubeTrackData

if TYPE_CHECKING:
    from bundle.discord.embeds import EmbedFactory

    from .player import GuildPlayer
    from .queue import TrackQueue

SEEK_UPDATE_INTERVAL = 5  # seconds between seek-bar refreshes


def _fmt_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def vc_status(vc: discord.VoiceProtocol | None) -> str:
    """Return 'Paused' or 'Playing' based on voice client state."""
    return "Paused" if vc and vc.is_paused() else "Playing"


class PlayerEmbed:
    """Manages the persistent now-playing message and seek-bar loop for one guild."""

    def __init__(
        self,
        embeds: EmbedFactory,
        queue: TrackQueue,
        player: GuildPlayer,
        text_channel: discord.TextChannel,
    ) -> None:
        self._embeds = embeds
        self._queue = queue
        self._player = player
        self.text_channel = text_channel

        self.msg: discord.Message | None = None
        self.view: discord.ui.View | None = None
        self._seek_task: asyncio.Task | None = None

    # ---- embed builders ----

    def now_playing(self, track: YoutubeTrackData, status: str) -> discord.Embed:
        return self._embeds.now_playing(
            title=track.title,
            author=track.author,
            duration_secs=track.duration,
            elapsed_secs=self._player.elapsed_secs(),
            status=status,
            queue_pos=self._queue.pos_str(),
            thumbnail_url=track.thumbnail_url or None,
        )

    def queue_page_count(self, per_page: int = 15) -> int:
        total = len(self._queue)
        if total == 0:
            return 1
        return (total + per_page - 1) // per_page

    def queue_embed(self, *, page: int = 0, per_page: int = 15) -> discord.Embed:
        total = len(self._queue)
        pages = self.queue_page_count(per_page)
        start = page * per_page
        end = min(start + per_page, total)

        lines: list[str] = []
        for i in range(start, end):
            track = self._queue.tracks[i]
            marker = "\u25B6" if i == self._queue.index else f"{i + 1}."
            lines.append(
                f"`{marker}` **{track.title}** \u2014 {track.author} `{_fmt_duration(track.duration)}`"
            )

        description = "\n".join(lines) or "Queue is empty."
        if self._queue.resolving:
            description += "\n*\u23F3 Still resolving...*"

        embed = self._embeds.info(
            title=f"Queue \u2014 {total} track(s)",
            description=description,
        )
        if pages > 1:
            embed.set_footer(text=f"Page {page + 1} / {pages}")
        return embed

    # ---- message lifecycle ----

    async def refresh(self, *, status: str) -> None:
        """Update the persistent message with current track state."""
        track = self._queue.current
        if not self.msg or not track:
            return
        try:
            await self.msg.edit(embed=self.now_playing(track, status), view=self.view)
        except discord.HTTPException:
            pass

    async def send_or_update(self, embed: discord.Embed, view: discord.ui.View | None = None) -> None:
        """Send a new message or edit the existing one."""
        if self.msg:
            try:
                await self.msg.edit(embed=embed, view=view)
                return
            except discord.NotFound:
                self.msg = None
        self.msg = await self.text_channel.send(embed=embed, view=view)

    def disable_view(self) -> None:
        """Disable all buttons and stop the view."""
        if not self.view:
            return
        for item in self.view.children:
            item.disabled = True  # type: ignore[union-attr]
        self.view.stop()

    async def delete(self) -> None:
        """Delete the persistent message and clean up the view."""
        self.disable_view()
        if self.msg:
            try:
                await self.msg.delete()
            except discord.HTTPException:
                pass
            self.msg = None

    async def show_error(self, description: str) -> None:
        """Update the persistent message with an error embed."""
        if not self.msg:
            return
        try:
            await self.msg.edit(
                embed=self._embeds.error(title="Music", description=description),
                view=self.view,
            )
        except discord.HTTPException:
            pass

    # ---- seek loop ----

    def start_seek_loop(self, guild: discord.Guild) -> None:
        if self._seek_task and not self._seek_task.done():
            self._seek_task.cancel()
        self._seek_task = asyncio.create_task(self._seek_loop(guild))

    def cancel_seek_loop(self) -> None:
        if self._seek_task and not self._seek_task.done():
            self._seek_task.cancel()

    async def _seek_loop(self, guild: discord.Guild) -> None:
        try:
            while True:
                await asyncio.sleep(SEEK_UPDATE_INTERVAL)
                if not self._queue.current:
                    return
                vc = guild.voice_client
                if not vc or not vc.is_playing():
                    continue  # paused -- don't update
                await self.refresh(status="Playing")
        except asyncio.CancelledError:
            return
