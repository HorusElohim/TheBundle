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

"""Core utility commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from bundle.core import logger, tracer

if TYPE_CHECKING:
    from ..bot import Bot

log = logger.get_logger(__name__)


class CoreCog(commands.Cog, name="core"):
    """Built-in utility commands."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.hybrid_command()
    @tracer.Async.decorator.call_raise
    async def ping(self, ctx: commands.Context) -> None:
        """Check bot responsiveness."""
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(f"{self.bot.brand_name} pong ({latency_ms}ms)")
