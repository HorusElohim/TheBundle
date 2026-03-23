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

"""Welcome new members joining a guild."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bundle.core import logger, tracer

if TYPE_CHECKING:
    from ..bot import Bot

log = logger.get_logger(__name__)


class GreetCog(commands.Cog, name="greet"):
    """Welcomes new members in the guild's system channel or the bot channel."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    @tracer.Async.decorator.call_raise
    async def on_member_join(self, member: discord.Member) -> None:
        channel = member.guild.system_channel or await self.bot.bot_channel(
            member.guild
        )
        await channel.send(embed=self.bot.embeds.welcome(member))
        log.info(f"Welcomed {member} in #{channel.name} ({member.guild.name})")
