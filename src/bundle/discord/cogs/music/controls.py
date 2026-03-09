"""Player control buttons -- discord.ui.View delegating to GuildPlayer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from . import MusicCog


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
        gs = self.cog._get_session(self.guild_id)
        vc = interaction.guild.voice_client
        if not gs or not vc:
            await interaction.response.send_message("Nothing playing.", ephemeral=True)
            return
        if gs.player.resume(vc):
            await gs.embed.refresh(status="Playing")
        elif gs.player.pause(vc):
            await gs.embed.refresh(status="Paused")
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
        gs = self.cog._get_session(self.guild_id)
        if not gs or not gs.queue:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        await interaction.response.send_message(embed=gs.embed.queue_embed(), ephemeral=True)
