# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Custom help command with branded embeds."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .embeds import Color

if TYPE_CHECKING:
    from .bot import Bot

# Cog display config: cog_name -> (emoji, display_name)
COG_META: dict[str, tuple[str, str]] = {
    "music": ("\U0001f3b5", "Music"),
    "youtube": ("\U0001f3ac", "YouTube"),
    "core": ("\U0001f527", "Utilities"),
}

# Cog display order (unlisted cogs appear at the end)
COG_ORDER = ["music", "youtube", "core"]


class BundleHelpCommand(commands.HelpCommand):
    """Branded help command using EmbedFactory styling."""

    @property
    def _bot(self) -> Bot:
        return self.context.bot  # type: ignore[return-value]

    def _base_embed(self, title: str, description: str = "") -> discord.Embed:
        e = self._bot.embeds
        return e._base(title=title, description=description, color=Color.INFO)

    # ---- !help ----

    async def send_bot_help(self, mapping: dict) -> None:
        bot = self._bot
        prefix = bot.config.command_prefix
        embed = self._base_embed(
            title=f"{bot.brand_name} \u2014 Commands",
            description=f"Use `{prefix}help <command>` for details on a specific command.",
        )

        # Build ordered cog list
        cogs_sorted = sorted(
            [c for c in bot.cogs.values() if self.get_bot_mapping().get(c)],
            key=lambda c: COG_ORDER.index(c.qualified_name) if c.qualified_name in COG_ORDER else 999,
        )

        for cog in cogs_sorted:
            cmds = await self.filter_commands(cog.get_commands(), sort=True)
            if not cmds:
                continue

            emoji, display = COG_META.get(cog.qualified_name, ("\u2699\ufe0f", cog.qualified_name))
            lines = [f"`{prefix}{cmd.qualified_name}` \u2014 {cmd.short_doc or 'No description'}" for cmd in cmds]
            embed.add_field(name=f"{emoji} {display}", value="\n".join(lines), inline=False)

        # Ungrouped commands (no cog)
        ungrouped = await self.filter_commands(mapping.get(None, []), sort=True)
        if ungrouped:
            lines = [f"`{prefix}{cmd.qualified_name}` \u2014 {cmd.short_doc or 'No description'}" for cmd in ungrouped]
            embed.add_field(name="\u2699\ufe0f Other", value="\n".join(lines), inline=False)

        await self.get_destination().send(embed=embed)

    # ---- !help <cog> ----

    async def send_cog_help(self, cog: commands.Cog) -> None:
        prefix = self._bot.config.command_prefix
        emoji, display = COG_META.get(cog.qualified_name, ("\u2699\ufe0f", cog.qualified_name))

        cmds = await self.filter_commands(cog.get_commands(), sort=True)
        lines = []
        for cmd in cmds:
            sig = f" {cmd.signature}" if cmd.signature else ""
            lines.append(f"`{prefix}{cmd.qualified_name}{sig}`\n{cmd.short_doc or 'No description'}")

        embed = self._base_embed(
            title=f"{emoji} {display}",
            description="\n\n".join(lines) or "No commands.",
        )
        await self.get_destination().send(embed=embed)

    # ---- !help <command> ----

    async def send_command_help(self, command: commands.Command) -> None:
        prefix = self._bot.config.command_prefix
        sig = f" {command.signature}" if command.signature else ""

        embed = self._base_embed(
            title=f"`{prefix}{command.qualified_name}{sig}`",
            description=command.help or command.short_doc or "No description.",
        )

        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{a}`" for a in command.aliases),
                inline=False,
            )

        await self.get_destination().send(embed=embed)

    # ---- !help <group> ----

    async def send_group_help(self, group: commands.Group) -> None:
        prefix = self._bot.config.command_prefix
        sig = f" {group.signature}" if group.signature else ""

        cmds = await self.filter_commands(group.commands, sort=True)
        lines = [f"`{prefix}{cmd.qualified_name}` \u2014 {cmd.short_doc or 'No description'}" for cmd in cmds]

        embed = self._base_embed(
            title=f"`{prefix}{group.qualified_name}{sig}`",
            description=(group.help or group.short_doc or "No description.") + "\n\n" + "\n".join(lines),
        )
        await self.get_destination().send(embed=embed)

    # ---- error ----

    async def send_error_message(self, error: str) -> None:
        embed = self._bot.embeds.error(title="Help", description=error)
        await self.get_destination().send(embed=embed)
