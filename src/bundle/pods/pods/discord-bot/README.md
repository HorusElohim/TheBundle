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

## Marvel Rivals stats

Create an API key at https://marvelrivalsapi.com/ and set MARVEL_RIVALS_API_KEY
in .discord.env. Never commit real keys.

Use the Discord slash command: /mr stats uid:75978910 season:21

The season argument is optional and defaults to the current season.
Discord requires subcommands before parameters, hence /mr stats uid:...
The prefix equivalent is !mr stats 75978910 21 (respecting DISCORD_BOT_PREFIX).

Stats come from https://docs.marvelrivalsapi.com/player-stats-19312751e0.
The provider is unofficial, requires a key, and may rate-limit or change its schema.
