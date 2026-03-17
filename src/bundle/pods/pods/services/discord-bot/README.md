# Discord Bot Pod

This pod starts the Discord music bot with:

```bash
bundle discord start
```

The bot reads its configuration from environment variables:

- `DISCORD_BOT_NAME`: display name used for logs and the dedicated text channel name.
- `DISCORD_BOT_TOKEN`: Discord bot token.
- `DISCORD_BOT_PREFIX`: optional command prefix, defaults to `!`.

## Usage

```bash
cd src/bundle/pods/pods/services/discord-bot
cp example.discord.env .discord.env

bundle pods build services/discord-bot
bundle pods run services/discord-bot
bundle pods logs services/discord-bot
bundle pods status services/discord-bot
```

### Dev mode

Mounts local source for fast iteration — no rebuild needed:

```bash
cd src/bundle/pods/pods/services/discord-bot
docker compose --profile dev up discord-bot-dev
```

## Notes

- The image uses `thebundle/bases/cpu` plus `ffmpeg` and a custom-built `libopus 1.6.1`.
- Runtime includes `ffmpeg`, which the music cog needs for voice playback.
- The bot creates a dedicated guild channel derived from `DISCORD_BOT_NAME` when needed.
