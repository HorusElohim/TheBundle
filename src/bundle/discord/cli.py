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

import rich_click as click

from bundle.core import tracer

from .bot import DEFAULT_BOT_NAME, BotConfig, run_bot


@click.group(name="discord")
def discord():
    """Discord bot commands."""
    pass


@discord.command()
@click.option(
    "--name",
    "bot_name",
    envvar="DISCORD_BOT_NAME",
    default=DEFAULT_BOT_NAME,
    show_default=True,
    help="Bot name used for logs and the dedicated guild channel (or set DISCORD_BOT_NAME).",
)
@click.option(
    "--token",
    envvar="DISCORD_BOT_TOKEN",
    required=True,
    help="Bot token (or set DISCORD_BOT_TOKEN).",
)
@click.option(
    "--prefix",
    envvar="DISCORD_BOT_PREFIX",
    default="!",
    help="Command prefix (or set DISCORD_BOT_PREFIX).",
)
@click.option(
    "--marvel-rivals-api-key",
    envvar="MARVEL_RIVALS_API_KEY",
    default=None,
    help="marvelrivalsapi.com key enabling the /mr commands (or set MARVEL_RIVALS_API_KEY).",
)
@tracer.Sync.decorator.call_raise
async def start(bot_name: str, token: str, prefix: str, marvel_rivals_api_key: str | None):
    """Start the Discord bot."""
    config = BotConfig(
        token=token,
        bot_name=bot_name.strip() or DEFAULT_BOT_NAME,
        command_prefix=prefix,
        marvel_rivals_api_key=marvel_rivals_api_key,
    )
    await run_bot(config)
