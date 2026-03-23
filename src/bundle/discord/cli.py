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

"""CLI for the Discord bot module."""

import os

import rich_click as click

from bundle.core import logger, tracer

from .bot import BotConfig, run_bot

log = logger.get_logger(__name__)


@click.group(name="discord")
def discord():
    """Discord bot commands."""
    pass


@discord.command()
@click.option(
    "--name",
    "bot_name",
    envvar="DISCORD_BOT_NAME",
    default=None,
    help="Bot name used for logs and the dedicated guild channel (or set DISCORD_BOT_NAME).",
)
@click.option(
    "--token",
    envvar="DISCORD_BOT_TOKEN",
    default=None,
    help="Bot token (or set DISCORD_BOT_TOKEN env var).",
)
@click.option(
    "--prefix",
    envvar="DISCORD_BOT_PREFIX",
    default="!",
    help="Command prefix (or set DISCORD_BOT_PREFIX).",
)
@tracer.Sync.decorator.call_raise
async def start(bot_name: str | None, token: str | None, prefix: str):
    """Start the Discord bot."""
    bot_name = (bot_name or os.environ.get("DISCORD_BOT_NAME") or "Bundle Bot").strip() or "Bundle Bot"
    if not token:
        token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        log.error("No bot token provided. Use --token or set DISCORD_BOT_TOKEN env var.")
        raise click.Abort()

    config = BotConfig(token=token, bot_name=bot_name, command_prefix=prefix)
    await run_bot(config)
