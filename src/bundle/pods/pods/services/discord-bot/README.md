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

## Marvel Rivals stats

Create an API key at https://marvelrivalsapi.com/ and set MARVEL_RIVALS_API_KEY
in .discord.env. Never commit real keys.

Use the Discord slash command: /mr stats uid:75978910 season:21

The season argument is optional and defaults to the current season.
Discord requires subcommands before parameters, hence /mr stats uid:...
The prefix equivalent is !mr stats 75978910 21 (respecting DISCORD_BOT_PREFIX).

Stats come from https://docs.marvelrivalsapi.com/player-stats-19312751e0.
The provider is unofficial, requires a key, and may rate-limit or change its schema.

## Game information commands

| Slash command | Description |
|---|---|
| `/mr meta` | Recent balance changes plus a link to live seasonal pick/win/ban rates |
| `/mr updates` | Latest game patch and balance notes, including new-hero announcements |
| `/mr champions` | Hero roster, optionally filtered by `role` and `page` |
| `/mr c list` | Short form of the hero roster |
| `/mr c stats query:Doctor Strange` | Aggregate hero performance by name or ID |

The data sources differ in scope: the hero-stats API returns unscoped
aggregate statistics, and the patch APIs provide dated releases. No supported
seasonal tier-list API was verified, so `/mr meta` **does not invent rankings**;
it links to a separate, labeled live meta source.
Data is fetched on request using the same `MARVEL_RIVALS_API_KEY`.
