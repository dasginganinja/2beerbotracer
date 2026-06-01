# Twitch Fixture Capture Design

Date: 2026-06-01

## Goal

Add opt-in Twitch chat fixture capture so live-tested chat interactions can become repeatable stub tests. The capture should record only the sanitized data needed to replay `handle_message()` behavior without connecting to Twitch.

## Current Context

- `trackracerbot.py` is the live Twitch path.
- Twitch command detection has been extracted into pure helpers and `classify_message()`.
- `handle_message()` still owns queue/file side effects and sends output through `print_everywhere()`.
- The TwitchIO outbound message queue must remain the only live Twitch send path.
- YouTube remains out of scope for this slice and must not poll or consume API quota.

## Chosen Approach

Add a small opt-in capture layer inside `trackracerbot.py`.

When capture is disabled, the bot behaves exactly as it does now. When capture is enabled with an environment variable, each handled Twitch message writes one sanitized JSONL record containing the incoming message metadata, command classification, moderator flag, and bot response strings.

Do not store raw TwitchIO objects. They may contain client/channel/event-loop state and are not useful for replayable tests.

## Capture Configuration

Use an environment variable:

```powershell
CHAT_CAPTURE_FILE=debug/chat-fixtures.jsonl
```

If `CHAT_CAPTURE_FILE` is unset or empty:

- no capture file is opened,
- no JSONL record is written,
- no runtime behavior changes.

The capture path should be local and developer-controlled. The implementation may create the parent directory if needed.

## Capture Record Shape

Each line is one JSON object for one incoming Twitch message:

```json
{
  "source": "twitch",
  "author": "example_user",
  "message": "!commands",
  "classification": "commands",
  "is_mod": true,
  "bot_outputs": [
    "Available commands: !play !entries // Mod Commands: !start !clearentries"
  ]
}
```

Required fields:

- `source`: always `twitch` for this slice.
- `author`: the author string passed to `handle_message()`.
- `message`: the incoming chat message string.
- `classification`: result of `classify_message(message)`.
- `is_mod`: result of the existing moderator detection helper for the Twitch message.
- `bot_outputs`: list of response strings sent through `print_everywhere()` for this incoming message.

Do not capture:

- OAuth tokens.
- Twitch client internals.
- raw TwitchIO message/channel/user objects.
- queue internals.
- full environment variables.
- YouTube API payloads.

## Hook Design

Hook capture inside `handle_message()` with a per-message local capture context.

At the start of `handle_message()`:

- compute `is_mod` using `is_moderator_message_source()`;
- compute `command` using `classify_message()`;
- create a local `capture_outputs` list.

Inside `handle_message()`, replace direct response calls with a local wrapper:

```python
async def respond(logmessage: str):
    capture_outputs.append(logmessage)
    await print_everywhere(logmessage, twitch_message=twitch_message)
```

Then `handle_message()` calls `await respond(...)` anywhere it currently calls `await print_everywhere(...)`.

At the end of `handle_message()`, write the JSONL record only if:

- `CHAT_CAPTURE_FILE` is configured;
- the message source is Twitch;
- capture is able to build the sanitized record.

The wrapper must still call `print_everywhere()`, so Twitch outbound queue behavior remains unchanged.

## Replayable Stub Testing

Captured records should be usable as test fixtures.

Tests should use tiny fake Twitch objects instead of TwitchIO:

```python
class FakeAuthor:
    def __init__(self, is_mod):
        self.is_mod = is_mod


class FakeTwitchMessage:
    def __init__(self, is_mod):
        self.author = FakeAuthor(is_mod)
```

Replay tests should:

- load one or more JSONL records;
- patch `print_everywhere()` to collect output strings instead of sending to Twitch;
- isolate `entry_queue`;
- isolate `entry_file_abs` to a temp file when a replayed message can mutate entries;
- call `handle_message()` with fake Twitch objects;
- assert emitted outputs match `bot_outputs`.

This creates repeatable "chat input produced bot output" coverage without Twitch, YouTube, sockets, or API quota.

## YouTube Later

The capture/replay pattern should be reusable for YouTube later, but this slice must not implement YouTube capture.

Future YouTube work can add:

- `source: "youtube"`;
- `is_owner`;
- `is_moderator`;
- replay using the existing `youtube_message={"authorDetails": ...}` dict shape.

That future work must be planned separately when YouTube behavior is the active priority.

## Risk Boundaries

This slice must not:

- enable YouTube polling;
- modify `testing.py`;
- store raw TwitchIO objects;
- bypass `print_everywhere()`;
- change Twitch outbound queue behavior;
- change response strings;
- change entry queue semantics;
- change daemon thread startup;
- change asyncio loop ownership.

Capture failures should not break the live bot. If writing the capture file fails, the bot should print a local warning and continue normal message handling.

## Testing

Add focused tests for:

- capture disabled does not attempt to write a capture record;
- capture enabled writes one Twitch JSONL record with source, author, message, classification, `is_mod`, and `bot_outputs`;
- capture records include multiple outputs if one handled message sends multiple responses;
- replay helper can run a captured Twitch fixture through `handle_message()` using fake Twitch objects and verify bot outputs;
- entry replay isolates queue/file state and does not touch live `entries.txt`;
- existing helper and structure tests still pass.

## Verification

Run verification from the activated project venv:

```powershell
. .\.venv-codex\Scripts\Activate.ps1
python -m pytest -q
python -m py_compile trackracerbot.py testing.py
```

Expected result:

- All tests pass.
- Both bot files compile.
- Only known third-party dependency warnings may appear.
