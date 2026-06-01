# Twitch Command Detection Refactor Design

Date: 2026-06-01

## Goal

Extract command and moderator detection helpers from `handle_message()` in `trackracerbot.py` while preserving the live Twitch bot's behavior. This is a low-risk Twitch-first slice that improves test coverage around pure functions before any larger runtime refactor.

## Current Context

- `trackracerbot.py` is the live Twitch path.
- `testing.py` is the Twitch plus YouTube experiment path and has drifted.
- The current uncommitted refactor already added `ENTRY_COMMANDS`, `ENTRY_EMOTE_PREFIXES`, `is_entry_message()`, and a guarded `main()`.
- The user live-tested the current Twitch bot successfully after that refactor.
- TwitchIO outbound message queue behavior must remain untouched.
- YouTube must not poll or consume API quota as part of this slice.

## Chosen Approach

Use a conservative helper-plus-classifier approach inside `trackracerbot.py`.

Add pure detection helpers for the command checks currently embedded in `handle_message()`, then add a pure classifier that maps a message string to one command category. Keep `handle_message()` responsible for all side effects and permission gates.

This gives individual functions enough surface area to test directly while avoiding changes to threading, async loop ownership, queue mutation, file writes, and Twitch sends.

## Architecture

Keep all changes in `trackracerbot.py` for this slice.

Retain the existing entry detection boundary:

- `ENTRY_COMMANDS`
- `ENTRY_EMOTE_PREFIXES`
- `is_entry_message(message: str) -> bool`

Add non-entry command helpers:

- `is_commands_message(message: str) -> bool`
- `is_start_message(message: str) -> bool`
- `is_clear_entries_message(message: str) -> bool`
- `is_entries_message(message: str) -> bool`

Add a pure classifier:

- `classify_message(message: str) -> str`

The classifier should return stable string labels such as:

- `commands`
- `entry`
- `start`
- `clear_entries`
- `entries`
- `unknown`

Add a moderator-source helper:

- `is_moderator_message_source(twitch_message=None, youtube_message=None) -> bool`

This helper preserves current Twitch and dormant YouTube compatibility checks. It must not start YouTube polling or change runtime startup.

## Behavior

The refactor must preserve current live behavior exactly.

`handle_message()` should still:

- Receive Twitch messages through the existing call path.
- Compute moderator status from the same Twitch and YouTube source fields.
- Mutate `entry_queue` only inside `handle_message()` or existing queue helpers.
- Write the entry file only through the existing file path.
- Send chat output only through `print_everywhere()`.
- Preserve all response strings exactly.
- Preserve mod-only enforcement for `!start` and `!clearentries`.

Command outcomes remain:

- `commands`: send `Available commands: !play !entries`, plus ` // Mod Commands: !start !clearentries` when the source is a moderator.
- `entry`: check duplicates, append to queue when room exists, write the entry file, and send the same success/full/duplicate responses.
- `start`: when moderator-only gate passes, send `Starting for ` plus the existing lineup format.
- `clear_entries`: when moderator-only gate passes, clear entries and send `All entries have been cleared.`
- `entries`: send `Race Entries: ` plus the existing queue join format.
- `unknown`: do nothing.

The classifier must not inspect author names, queue contents, Twitch channel objects, YouTube polling state, async objects, or filesystem state.

## Ordering

Preserve the current command check ordering:

1. `!commands`
2. entry command or entry emote
3. `!start`
4. `!clearentries`
5. `!entries`
6. unknown

The command prefixes do not currently conflict, but preserving order keeps the refactor behaviorally honest.

## Risk Boundaries

This slice must not:

- Modify TwitchIO outbound queue behavior.
- Add direct Twitch sends outside `print_everywhere()`.
- Change daemon thread startup.
- Change asyncio loop ownership.
- Start, enable, or poll YouTube.
- Merge behavior from `testing.py`.
- Rework race-entry state management.
- Introduce a service object or new module.
- Delete or revert unrelated loose workspace files.

## Testing

Expand tests around pure helpers before or alongside the refactor.

Helper tests should cover:

- `!commands` recognition, including case-insensitive matching.
- `!entries` recognition, including case-insensitive matching.
- `!start` recognition, including case-insensitive matching.
- `!clearentries` recognition, including case-insensitive matching.
- Rejection of ordinary non-command chat.
- Existing entry command and emote behavior, including prefix-only emote matching.

Classifier tests should cover:

- Each known command category.
- Entry commands and entry emote prefixes.
- Plain chat returning `unknown`.
- Current ordering assumptions.

Moderator helper tests should cover:

- Twitch message with author `is_mod=True`.
- Twitch message with author `is_mod=False`.
- Twitch message with missing author.
- YouTube owner and moderator flags preserving current compatibility behavior.
- YouTube non-owner/non-moderator source returning false.

Async `handle_message()` tests are optional for this slice. If added, they should patch `print_everywhere()` and file writes carefully. The main purpose of this slice is to make command interpretation provable through pure helper tests.

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
- Only known third-party warnings may appear.

## Out Of Scope

- YouTube enable/disable controls.
- YouTube quota behavior.
- Single event loop architecture.
- Race-entry state object extraction.
- Moving command configuration into a new module.
- WebSocket behavior changes.
- Runtime dashboard or widget changes.
