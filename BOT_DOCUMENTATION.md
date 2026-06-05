# 2BeerBotRacer Documentation

## Overview
This bot manages race entries for 2Beer Minimum Racing across Twitch and YouTube chat.

---

## Emote Entry System

The following emotes automatically trigger a race entry (equivalent to typing `!race`):

| Emote | Description |
|-------|-------------|
| `2BeerShrek` | Official race entry emote |
| `avoidr3Hotdogman` | Race entry emote |
| `artmannJudy` | Race entry emote |
| `x100pr3Hndoclap52` | Race entry emote |
| `spacec122GoodVibes` | Race entry emote |
| `artmannNatmar` | Race entry emote |
| `artmannOhyeah` | Race entry emote |
| `x2beerShrek` | Race entry emote |
| `x2beerRace` | Race entry emote |

**How Emote Entries Work:**

When a chat message **starts with** any of these emote strings (e.g., `artmannJudy`), the bot treats it as a race entry command. The bot checks:
1. Is the message starting with a recognized race entry emote?
2. Has this user already entered (checking `entry_queue`)?
3. Is there room in the queue (`len(entry_queue) < MAX_ENTRIES`)?

If all checks pass, the user is added to the queue and notified.

---

## Mod Commands

### Admin Commands (Available to Moderators Only)

| Command | Description |
|---------|-------------|
| `!start` | Removes up to `MAX_ENTRIES` (default: 30) entries from the queue and announces the starting lineup |
| `!clearentries` | Clears all race entries from the queue and file |
| `!winner <number or name>` | Records the winner for the latest pending race |
| `!setlastwinner <number, name, skipped, or unknown>` | Corrects the latest race result |

### Regular User Commands

| Command | Description |
|---------|-------------|
| `!commands` | Lists available commands |
| `!entries` | Shows current race entry list |
| `!winner` | Shows the latest race winner or latest race winner status |
| `!leaderboard` | Shows the top 5 winners with compact stats |
| `!stats [name]` | Shows your stats, or another racer's stats when a name is provided |
| `!carstats <number>` | Shows win stats for a car number across recorded races |
| `!carleaderboard` | Shows the top winning car numbers |
| `!race` / `!play` / `!enter` / `!join` | Submit a race entry |

---

## WebSocket Server

The bot runs a WebSocket server that exposes race entry data to external clients (like the HTML dashboard).

### Server Configuration

- **Host**: `0.0.0.0` (all interfaces)
- **Port**: `64209`
- **Path**: `/` (root)

### API Endpoints

The WebSocket uses a simple command-based protocol:

| Message | Response | Description |
|---------|----------|-------------|
| `send_queue` | JSON array | Returns current race entries as a JSON object with `number` and `name` fields |
| `latest_winner` | JSON object | Returns the latest race winner status and winner stats |

### HTML Client Connection

The HTML dashboard (`browsersource-*.html`) connects to the WebSocket at:
```
ws://localhost:64209
```

The client:
1. Establishes a WebSocket connection
2. Automatically sends `send_queue` to refresh the entry table
3. Reconnects every 5 seconds if disconnected
4. Updates the DOM table with new entry data

### Data Format

The `send_queue` response is a JSON array:
```json
[
  {"number": 1, "name": "username1"},
  {"number": 2, "name": "username2"},
  ...
]
```

Note: Entry #29 is automatically changed to #69 per Art's request.

---

## Message Queue System

The bot uses a thread-safe message queue to handle Twitch's rate limits:

- **Rate Limit**: ~20 messages per 30 seconds for regular users
- **Bot Strategy**: Waits 1.5 seconds between messages (20 per 30s)
- **Retry Logic**: Up to 3 retries on cooldown errors
- **Background Processing**: Messages are queued and processed asynchronously

---

## Entry File

- **Default Location**: `entries.txt` (configurable via `ENTRY_FILE` env var)
- **Purpose**: Persists race entries across bot restarts
- **Format**: One username per line
- **Max Entries**: 30 entries before the list is considered full

---

## YouTube Integration

The bot listens to YouTube live chat via the YouTube Data API v3 to capture race entries from YT chat.

### How It Works

1. **Get Chat ID**: The bot queries the YouTube API to get the `activeLiveChatId` for the live stream:
   ```
   GET /youtube/v3/videos/{videoId}
   Parameters: part=liveStreamingDetails,id={videoId}
   ```

2. **Poll Messages**: The bot polls the live chat messages endpoint at configurable intervals:
   ```
   GET /youtube/v3/liveChat/messages
   Parameters: liveChatId={chatId}, part=snippet,authorDetails,pageToken={token}
   ```

3. **Process Each Message**: For each message:
   - Parse the message timestamp to detect new messages
   - Extract `messageText` from `textMessageDetails`
   - Extract `displayName` from `authorDetails`
   - Check if the message is a race entry command or emote
   - Call `handle_message()` to process the entry

4. **Rate Limiting**: Uses `YOUTUBE_TIMEOUT` (default: 120s) to avoid hitting API rate limits. Can be reduced to 3s with `!ytenable`.

### YouTube Commands

| Command | Description |
|---------|-----|
| `!ytenable` | Reduces polling interval to 3s (active mode) |
| `!ytdisable` | Returns to 120s polling interval |

### Configuration

- `YOUTUBE_API_KEY`: YouTube Data API key
- `YOUTUBE_LIVE_VIDEO_ID`: YouTube live stream video ID
- `YOUTUBE_TIMEOUT_DEFAULT`: Default polling interval (120s)
- `YOUTUBE_TIMEOUT_ACTIVE`: Active polling interval (3s)

Note: The YouTube integration runs independently of Twitch and continues even after Twitch stops polling.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TWITCH_CLIENT_ID` | Twitch OAuth client ID |
| `TWITCH_CLIENT_SECRET` | Twitch OAuth client secret |
| `TWITCH_ACCESS_TOKEN` | Twitch access token |
| `TWITCH_REFRESH_TOKEN` | Twitch refresh token |
| `TWITCH_CHANNEL` | Twitch channel to listen to |
| `TWITCH_BOT_NAME` | Name of the bot in chat |
| `YOUTUBE_API_KEY` | YouTube Data API key |
| `YOUTUBE_LIVE_VIDEO_ID` | YouTube live stream video ID |
| `ENTRY_FILE` | Path to the entry file (default: `entries.txt`) |
| `RACE_HISTORY_DB` | SQLite database path for durable race history (default: `race-history.sqlite3`) |

---

## Thread Architecture

The bot runs multiple threads in parallel:

1. **WebSocket Thread**: Handles WebSocket connections and client data
2. **Twitch Thread**: Listens to Twitch chat and processes commands
3. **YouTube Thread** (optional): Polls YouTube chat (30s intervals)

All threads are daemon threads and terminate when the main process exits.
