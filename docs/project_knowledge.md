# Track Racer Bot Project Knowledge

This file records current project knowledge and working conventions so future work can resume without rediscovering the same details.

## Working Rules

- Always use a Python virtual environment when working on this project.
- Activate the venv before running Python, pip, tests, or the bot so PATH and script resolution match normal project usage.
- The original `.venv` currently points at a missing Windows Store Python path and should not be trusted until rebuilt.
- A fresh local venv was created at `.venv-codex` with Python 3.12.13.
- Current activation command:

```powershell
. .\.venv-codex\Scripts\Activate.ps1
```

- After activation, run Python commands through the activated environment, for example:

```powershell
python -m py_compile trackracerbot.py testing.py
```

## Current Git State

- Current branch: `message-queue`.
- The branch is ahead of `origin/message-queue` by one local commit:
  - `611a221 Add bot documentation.`
- Message queue work on this branch includes:
  - `a3fdd97 Add rate limiting message queue`
  - `2cdb341 queue adjustements after testing`
  - `611a221 Add bot documentation.`
- Compared with `origin/master`, this branch adds the Twitch output queue/rate limiting work and bot documentation.
- At the time this was logged, there were uncommitted local edits to:
  - `requirements.txt`
  - `trackracerbot.py`
- At the time this was logged, there were untracked workspace files, including generated/browser-source variants, widget HTML files, `docs/`, `.claude/`, `natmar.py`, backup entry files, and `__pycache__/`.

## Verification Snapshot

- Syntax check passed using the fresh venv:

```powershell
. .\.venv-codex\Scripts\Activate.ps1
python -m py_compile trackracerbot.py testing.py
```

- No full runtime test was performed because that requires real Twitch/YouTube credentials and live service access.

## Main Bot File

- Primary runtime file: `trackracerbot.py`.
- Older/test variant: `testing.py`.
- Entry persistence file defaults to `entries.txt` unless `ENTRY_FILE` is set.
- `entries.txt` is ignored by Git because it is runtime state.
- Default maximum queue length is `MAX_ENTRIES = 30`.

## Runtime Architecture

- The bot uses multiple daemon threads:
  - WebSocket server thread.
  - Twitch bot thread.
  - YouTube listener is currently present but commented out in `trackracerbot.py`.
- `trackracerbot.py` starts:
  - `setup_websocket()` in a daemon thread.
  - `listen_to_twitch()` in a daemon thread.
  - `twitch_thread.join()` to keep the process alive.
- `testing.py` has YouTube polling enabled with `asyncio.run(listen_to_youtube())`.

## Twitch Message Queue

- `trackracerbot.py` has a Twitch output queue to avoid rate-limit errors.
- The queue is initialized when the Twitch bot is ready.
- `print_everywhere()` prints locally and queues Twitch sends instead of sending immediately when the queue exists.
- `_process_message_queue()` sends queued messages with `MESSAGE_RATE_LIMIT = 1.5` seconds between sends.
- Cooldown handling retries up to 3 times and attempts to parse the cooldown seconds from `IRCCooldownError`.

## Chat Commands

- User commands:
  - `!commands`
  - `!entries`
  - `!race`
  - `!play`
  - `!enter`
  - `!join`
- Moderator commands:
  - `!start`
  - `!clearentries`
- `testing.py` also includes YouTube polling controls:
  - `!ytenable`
  - `!ytdisable`

## Race Entry Emotes

`trackracerbot.py` currently treats messages starting with these strings as race entries:

- `artmannJudy`
- `x100pr3Hndoclap52`
- `x2beerShrek`
- `avoidr3Hotdogman`
- `spacec122GoodVibes`
- `artmannNatmar`
- `artmannOhyeah`

Important detail: the current working tree changed these checks from substring matching with `message.count(...)` to prefix matching with `message.startswith(...)`.

## WebSocket Behavior

- WebSocket server listens on port `64209`.
- `send_queue` returns JSON for the current entry queue.
- `latest_winner` attempts to return the global `latest_winner`.
- `entries_json()` returns objects in this shape:

```json
[
  {"number": 1, "name": "username"}
]
```

- Entry number 29 is displayed as 69.

## Documentation Already Present

- `BOT_DOCUMENTATION.md` documents:
  - Emote entry system.
  - Twitch and moderator commands.
  - WebSocket protocol.
  - Message queue behavior.
  - Entry file behavior.
  - YouTube integration.
  - Environment variables.
  - Thread architecture.
- `docs/refactor_handoff.md` is an untracked handoff note proposing a future refactor to:
  - Single event loop.
  - SQLite winner DB.
  - New `main.py`.
  - WebSocket winner export.

## Environment Variables

Known variables used by the bot:

- `TWITCH_CLIENT_ID`
- `TWITCH_CLIENT_SECRET`
- `TWITCH_ACCESS_TOKEN`
- `TWITCH_REFRESH_TOKEN`
- `TWITCH_CHANNEL`
- `TWITCH_BOT_NAME`
- `YOUTUBE_API_KEY`
- `YOUTUBE_LIVE_VIDEO_ID`
- `ENTRY_FILE`

`.env` is ignored and should remain local.

## Known Cleanup Items

- Decide whether the `trackracerbot.py` emote change from `count` to `startswith` is intentional and commit or revert it.
- `requirements.txt` appears to contain null-byte/UTF-16-style encoding and was locally reduced to a smaller dependency set. Confirm the intended dependency list and normalize the file.
- Decide whether untracked HTML/widget files and `natmar.py` should be tracked, ignored, or removed.
- Push or otherwise preserve the local documentation commit if it is accepted.
- Rebuild the project venv from a clean, normalized requirements file when dependencies need to be installed.
