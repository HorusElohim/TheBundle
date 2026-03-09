"""Player control buttons -- discord.ui.View delegating to GuildPlayer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .embed import PlayerEmbed
    from . import MusicCog


class QueuePaginator(discord.ui.View):
    """Paginated queue browser with prev/next buttons."""

    def __init__(self, embed_mgr: PlayerEmbed, *, timeout: float = 120) -> None:
        super().__init__(timeout=timeout)
        self._embed = embed_mgr
        self._page = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        pages = self._embed.queue_page_count()
        self.btn_prev_page.disabled = self._page <= 0
        self.btn_next_page.disabled = self._page >= pages - 1

    @discord.ui.button(label="\u25C0", style=discord.ButtonStyle.secondary)
    async def btn_prev_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self._page = max(0, self._page - 1)
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self._embed.queue_embed(page=self._page), view=self,
        )

    @discord.ui.button(label="\u25B6", style=discord.ButtonStyle.secondary)
    async def btn_next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self._page = min(self._embed.queue_page_count() - 1, self._page + 1)
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self._embed.queue_embed(page=self._page), view=self,
        )


class PlayerControls(discord.ui.View):
    """Five-button control strip attached to the now-playing embed."""

    def __init__(self, cog: MusicCog, guild_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(emoji="\u23EE\uFE0F", style=discord.ButtonStyle.secondary)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self.cog._advance(interaction.guild, -1)

    @discord.ui.button(emoji="\u23EF\uFE0F", style=discord.ButtonStyle.primary)
    async def btn_pause(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self.cog._get_session(self.guild_id):
            await interaction.response.send_message("Nothing playing.", ephemeral=True)
            return
        await interaction.response.defer()
        if not await self.cog._resume_guild(interaction.guild):
            await self.cog._pause_guild(interaction.guild)

    @discord.ui.button(emoji="\u23ED\uFE0F", style=discord.ButtonStyle.secondary)
    async def btn_skip(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self.cog._advance(interaction.guild, +1)

    @discord.ui.button(emoji="\u23F9\uFE0F", style=discord.ButtonStyle.danger)
    async def btn_stop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await self.cog._stop_guild(interaction.guild)

    @discord.ui.button(emoji="\U0001F4CB", style=discord.ButtonStyle.secondary)
    async def btn_queue(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        gs = self.cog._get_session(self.guild_id)
        if not gs or not gs.queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        paginator = QueuePaginator(gs.embed)
        await interaction.response.send_message(
            embed=gs.embed.queue_embed(page=0), view=paginator, ephemeral=True,
        )
