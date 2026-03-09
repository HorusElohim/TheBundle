# Music Cog

Queue-based YouTube audio streaming for Discord with interactive controls, paginated queue browsing, and automatic voice lifecycle management.

---

## Architecture

The cog is split into focused modules with clear separation of concerns:

```
music/
  __init__.py   MusicCog + GuildSession  -- orchestrator, commands, session management
  queue.py      TrackQueue               -- pure data: ordered list with cursor
  player.py     GuildPlayer              -- FFmpeg playback, timing, pause/resume
  embed.py      PlayerEmbed              -- message lifecycle, seek-bar loop, embed builders
  controls.py   PlayerControls           -- button views (player strip + queue paginator)
```

### Module Responsibilities

| Module | Class | Role |
|--------|-------|------|
| `queue.py` | `TrackQueue` | Ordered track list with cursor navigation, shuffle. No Discord imports. |
| `player.py` | `GuildPlayer` | Owns FFmpeg voice playback, elapsed time tracking, pause offset math. |
| `embed.py` | `PlayerEmbed` | Manages the persistent now-playing message, seek-bar refresh loop, and all embed states (playing, paused, stopped, finished, error). |
| `controls.py` | `PlayerControls` | Six-button strip: prev, pause/resume, skip, stop, shuffle, queue. |
| `controls.py` | `QueuePaginator` | Prev/next page buttons for browsing the full queue. |
| `__init__.py` | `GuildSession` | Dataclass bundling per-guild queue, player, embed, and async tasks. |
| `__init__.py` | `MusicCog` | Top-level orchestrator: hybrid commands, resolution pipeline, voice lifecycle timers, event listeners. |

---

## Commands

All commands are **hybrid** -- they work as both prefix (`!play`) and slash (`/play`) commands.

| Command | Description |
|---------|-------------|
| `/play <url>` | Add a YouTube video or playlist to the queue and start playing. |
| `/skip` | Skip to the next track. |
| `/prev` | Go back to the previous track. |
| `/pause` | Pause playback. |
| `/resume` | Resume paused playback. |
| `/shuffle` | Shuffle the remaining (upcoming) tracks in the queue. |
| `/queue` | Display the current queue with pagination. |
| `/stop` | Stop playback, clear the queue, and disconnect. |

## Player Controls

The now-playing embed includes an interactive button strip:

| Button | Action |
|--------|--------|
| ⏮️ | Previous track |
| ⏯️ | Toggle pause / resume |
| ⏭️ | Skip to next track |
| ⏹️ | Stop and disconnect |
| 🔀 | Shuffle upcoming tracks |
| 📋 | Show paginated queue (ephemeral) |

---

## Voice Lifecycle

The cog manages voice connections automatically:

- **Alone timeout** (`30s`): If the bot is left alone in a voice channel, it disconnects after 30 seconds.
- **Pause timeout** (`5min`): If playback is paused for more than 5 minutes, the bot disconnects.
- **Force-disconnect handling**: If the bot is manually disconnected by a user, it cleans up its session gracefully.
- **Stale client recovery**: Detects and recovers from stale `VoiceClient` references after prior disconnects.

---

## Resolution Pipeline

When `/play` is invoked:

1. The bot connects to the user's voice channel (or moves if already connected).
2. A `GuildSession` is created (or reused) for the guild.
3. An async task resolves the URL via `bundle.youtube.pytube` -- tracks stream in one at a time.
4. The first resolved track starts playing immediately; subsequent tracks are queued.
5. If the queue empties while tracks are still resolving, a "waiting" state is shown until the next track arrives.
6. If all resolution completes and nothing is left, the bot shows "Finished" and disconnects.

---

## Seek Bar

The now-playing embed includes a visual seek bar that updates every **5 seconds** during playback. It pauses updates while the player is paused and resumes when playback continues.
