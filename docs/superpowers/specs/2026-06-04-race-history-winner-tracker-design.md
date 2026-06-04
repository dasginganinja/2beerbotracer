# Race History Winner Tracker Design

## Goal

Add durable race history tracking to the bot so moderators can record winners, viewers can see the latest winner, and chat can query leaderboard and racer stats. Race records are created when a moderator starts a race, not when entries open.

## Current Context

- `trackracerbot.py` owns command parsing, entry queue mutation, registration state, chat responses, and Twitch fixture capture.
- `entry_queue` is the live signup list and persists to `entries.txt`.
- `bot-state.json` stores transient registration and submission timing state.
- The existing `!entry` lookup helpers already support number-or-name lookup and the special display number rule where position 29 displays as car 69.
- The WebSocket route for `latest_winner` exists, but no durable `latest_winner` state is defined or maintained.

## Approach

Use a new SQLite-backed `race_history.py` module built on Python's stdlib `sqlite3`. This keeps historical data durable and queryable without adding dependencies. `trackracerbot.py` will keep command dispatch and chat response wiring, while `race_history.py` owns schema creation, race writes, winner corrections, leaderboard queries, and racer stats.

Rejected alternatives:

- Append-only JSONL is easy to append but makes corrections, leaderboard queries, and stats unnecessarily awkward.
- Extending `bot-state.json` mixes durable history with transient runtime state and will become fragile as race history grows.

## Data Model

Default database path:

- Environment variable: `RACE_HISTORY_DB`
- Default: `race-history.sqlite3` beside the entry file
- The generated DB file must be ignored by Git.

Tables:

```text
races
- id integer primary key
- started_at_utc text not null
- ended_at_utc text null
- entries_opened_at_utc text null
- entries_closed_at_utc text null
- status text not null       -- pending, completed, skipped, unknown
- winner_entry_id integer null
- winner_name text null
- created_by text null
- updated_at_utc text not null

race_entries
- id integer primary key
- race_id integer not null
- position integer not null
- display_number integer not null
- name text not null
- normalized_name text not null
```

Historical timestamps use ISO-8601 UTC wall-clock time. Existing `submission_stats.started_at` remains monotonic runtime state for elapsed signup timing and should not be used as historical time.

Add lightweight wall-clock submission window tracking to runtime state so historical records can store when entries opened and closed. `!clearentries` and `!openentries` set `entries_opened_at_utc`; `!closeentries` and `!start` set `entries_closed_at_utc`. These timestamps can live in `bot-state.json` until copied into a race row at `!start`.

## Race Lifecycle

- `!clearentries` and `!openentries` keep their current entry behavior and do not create race records.
- Mod `!start` creates a race record from the current `entry_queue` snapshot and locks registration.
- Empty `!start` is blocked with: `No entries to start.`
- New race entries are copied into `race_entries` with stored position, display number, and username.
- A race starts with status `pending`.
- If `!start` sees a latest `pending` race:
  - If the stored race entry snapshot matches the current `entry_queue`, treat it as an intentional double-start override. Delete that pending race and create a fresh pending race with the current start timestamp, then announce the current lineup.
  - If the entry snapshot differs from the current `entry_queue`, refuse the new start with: `Record the last winner first: !winner {number or name}. Use !setlastwinner skipped if there was no winner.`
- A completed race has one stored winner from that race's stored entries.
- A skipped race means no winner should be counted.
- An unknown race means the race happened, but the winner was not captured.

## Commands

Use strict command matching for new commands: exact command or command plus a space. This avoids false positives such as `!winnerboard`.

### `!winner`

Public read command when called with no arguments.

- If latest race is completed: show the latest winner and compact stats.
- If latest race is pending: show that the latest race has no winner recorded yet.
- If latest race is skipped or unknown: show that state clearly.
- If there is no history: `No races recorded yet.`

Example:

```text
Last winner: racer_one. 3W / 12R / 25.0%.
```

### `!winner <number|name>`

Moderator-only write command.

- Records the winner for the latest pending race.
- Resolves the argument against the latest race's stored entries, not the current queue.
- Uses the same number-or-name lookup behavior as `!entry`, including car 69.
- If no pending race exists, respond with a short error and do not write history.
- If the argument does not match an entry in that race, respond with a short error and do not write history.

Example:

```text
Winner recorded: racer_one. 3W / 12R / 25.0%.
```

### `!setlastwinner <number|name|skipped|unknown>`

Moderator-only correction command.

- Updates the latest race even if it is already completed, skipped, or unknown.
- Number/name arguments resolve against the latest race's stored entries.
- `skipped` marks the latest race as skipped and does not count a win.
- `unknown` marks the latest race as unknown and does not count a win.
- The response includes the winner's compact stats when setting a concrete winner.

### `!leaderboard`

Public read command.

- Shows the top 5 racers by completed wins.
- Includes compact stats for each racer.
- If there are no completed winners: `No completed winners yet.`

Example:

```text
Top winners: 1. racer_one 5W/20R 25.0%; 2. racer_two 3W/10R 30.0%.
```

### `!stats [number|name]`

Public read command.

- `!stats` shows the caller's stats.
- `!stats <name>` shows stats for a normalized username across history.
- `!stats <number>` looks up that car number in the latest race entries. If no latest race entry matches, respond with a clear no-match message.
- If no race stats exist for the selected user: `No race stats found for {name}.`

### `!commands`

Update command help:

- Public list includes `!winner`, `!leaderboard`, and `!stats`.
- Moderator list includes `!winner <number|name>` and `!setlastwinner`.

## Stats Semantics

- Total races for a user means every stored race where they appeared in the entry snapshot.
- Wins count only completed races where the user is the recorded winner.
- Win percentage is `wins / total races * 100`, rounded to one decimal.
- Case-insensitive matching is used for lookup.
- Responses preserve stored display casing, preferring the latest observed casing.
- Pending, skipped, and unknown races count toward total races but not wins.

## Shared Lookup Logic

Extract or generalize the existing entry lookup helpers so the same behavior works for both live queues and stored race entries:

- `display_car_number(position)`
- display-number lookup
- normalized username lookup
- response helpers for no-match cases

This keeps `!entry`, `!winner`, `!setlastwinner`, and `!stats <number|name>` consistent.

## WebSocket Behavior

Replace the current undefined `latest_winner` behavior with data from race history. The WebSocket response should return a JSON object describing the latest race status and winner when available. It should handle no-history and pending/unknown/skipped states without referencing undefined globals.

## Testing

Add focused tests before implementation changes:

- `race_history.py` unit tests with temporary SQLite database files.
- Schema initialization and idempotent startup.
- Race creation with stored entries and display numbers.
- Winner completion, skipped, unknown, and correction flows.
- Leaderboard ordering and racer stats calculations.
- Command helper tests for `!winner`, `!setlastwinner`, `!leaderboard`, and `!stats`.
- Async `handle_message()` tests for:
  - empty `!start` blocked
  - `!start` creates a pending race
  - same-lineup double `!start` override
  - changed-lineup `!start` refusal while previous race is pending
  - mod-only winner mutation
  - public latest winner lookup
  - set-last-winner corrections
  - skipped and unknown states
  - leaderboard and stats responses
- Twitch fixture replay update for new commands.
- Existing Python and Node tests must continue passing.

## Scope Boundaries

In scope:

- Durable SQLite race history.
- Winner, correction, leaderboard, and stats commands.
- WebSocket latest winner backed by race history.
- Documentation updates for the new commands and database setting.

Out of scope:

- Major runtime/threading refactor.
- UI/widget changes beyond preserving existing WebSocket compatibility.
- Backfilling historical races from old entry files.
- Removing existing entry queue persistence.

## Open Risks

- `trackracerbot.py` is already broad. Keep new history logic in `race_history.py` and limit bot-file edits to command parsing, response building, and orchestration.
- Existing docs say `!start` removes entries, but current code does not. This feature should follow current behavior and can document the actual behavior.
- The term `stats` already appears in `submission_stats`; implementation should name race-stat helpers clearly to avoid confusion.
