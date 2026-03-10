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
cd src/bundle/pods/pods/discord-bot
cp example.discord.env .discord.env

bundle pods build discord-bot
bundle pods run discord-bot
bundle pods logs discord-bot
bundle pods status discord-bot
```

## Notes

- The image installs the local package with the `discord` and `youtube` extras.
- Runtime includes `ffmpeg`, which the music cog needs for voice playback.
- The bot creates a dedicated guild channel derived from `DISCORD_BOT_NAME` when needed.
