# Stream Race Stats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public `!streamracestats` command that summarizes stream-day races from the local noon cutoff in one or two chat messages.

**Architecture:** Add the stream-window aggregation in `race_history.py` so timestamp/status/winner queries stay with persistence code. Keep local noon cutoff calculation, command routing, and chat formatting in `trackracerbot.py`, matching existing command-handler patterns.

**Tech Stack:** Python, SQLite, pytest, existing Twitch fixture replay tests.

---

## File Structure

- Modify `race_history.py`: add `get_stream_race_summary(db_path, started_at_or_after_utc)` to return counts, chronological winner entries, top drivers, top cars, and unique winner count.
- Modify `trackracerbot.py`: add `!streamracestats` constants/classification, local noon cutoff helper, response builders, and command handler.
- Modify `tests/test_race_history.py`: add aggregate tests for race-window stats.
- Modify `tests/test_twitch_fixture_capture.py`: add command-output tests and fixture replay case.
- Modify `tests/fixtures/twitch/all_commands.jsonl`: add empty command case.
- Modify `README.md` and `BOT_DOCUMENTATION.md`: document the public command.

### Task 1: Race History Stream Summary

**Files:**
- Modify: `race_history.py`
- Test: `tests/test_race_history.py`

- [ ] **Step 1: Write failing aggregate tests**

Add tests that seed races before and after a cutoff, including completed, pending, skipped, and unknown statuses:

```python
def test_get_stream_race_summary_counts_window_and_winners(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["OldWinner"], started_at_utc="2026-06-05T15:59:00+00:00")
    race_history.complete_latest_pending_race(str(db_path), "OldWinner")
    race_history.start_race(str(db_path), ["Alice", "Bob"], started_at_utc="2026-06-05T16:00:00+00:00")
    race_history.complete_latest_pending_race(str(db_path), "Alice")
    race_history.start_race(str(db_path), ["Cara", "Dan"], started_at_utc="2026-06-05T16:15:00+00:00")
    race_history.complete_latest_pending_race(str(db_path), "Dan")
    race_history.start_race(str(db_path), ["Alice", "Eli"], started_at_utc="2026-06-05T16:30:00+00:00")
    race_history.complete_latest_pending_race(str(db_path), "Alice")
    race_history.start_race(str(db_path), ["Pending"], started_at_utc="2026-06-05T16:45:00+00:00")
    race_history.start_race(str(db_path), ["Skipped"], started_at_utc="2026-06-05T17:00:00+00:00")
    race_history.set_latest_race_result(str(db_path), "skipped")
    race_history.start_race(str(db_path), ["Unknown"], started_at_utc="2026-06-05T17:15:00+00:00")
    race_history.set_latest_race_result(str(db_path), "unknown")

    assert race_history.get_stream_race_summary(str(db_path), "2026-06-05T16:00:00+00:00") == {
        "total": 6,
        "completed": 3,
        "pending": 1,
        "skipped": 2,
        "winners": [
            {"name": "Alice", "display_number": 1},
            {"name": "Dan", "display_number": 2},
            {"name": "Alice", "display_number": 1},
        ],
        "top_drivers": [
            {"name": "Alice", "wins": 2},
            {"name": "Dan", "wins": 1},
        ],
        "top_cars": [
            {"display_number": 1, "wins": 2},
            {"display_number": 2, "wins": 1},
        ],
        "unique_winners": 2,
    }
```

Add an empty-window test:

```python
def test_get_stream_race_summary_returns_empty_counts(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"

    assert race_history.get_stream_race_summary(str(db_path), "2026-06-05T16:00:00+00:00") == {
        "total": 0,
        "completed": 0,
        "pending": 0,
        "skipped": 0,
        "winners": [],
        "top_drivers": [],
        "top_cars": [],
        "unique_winners": 0,
    }
```

- [ ] **Step 2: Run failing aggregate tests**

Run:

```powershell
.\.venv-codex\Scripts\python.exe -m pytest tests\test_race_history.py -k "stream_race_summary" -v
```

Expected: fail because `get_stream_race_summary` does not exist.

- [ ] **Step 3: Implement aggregate helper**

Add `get_stream_race_summary(db_path: str, started_at_or_after_utc: str) -> dict` that:

- Filters `races.started_at_utc >= ?`.
- Counts total, completed, pending, and skipped-plus-unknown.
- Joins completed winners to `race_entries` by `winner_entry_id`.
- Orders `winners` chronologically by race id.
- Builds top drivers from completed winners by normalized name, wins desc, name asc.
- Builds top cars from completed winners by display number, wins desc, display number asc.

- [ ] **Step 4: Run aggregate tests**

Run:

```powershell
.\.venv-codex\Scripts\python.exe -m pytest tests\test_race_history.py -k "stream_race_summary" -v
```

Expected: pass.

### Task 2: Chat Command and Formatting

**Files:**
- Modify: `trackracerbot.py`
- Test: `tests/test_twitch_fixture_capture.py`
- Test: `tests/test_trackracerbot_helpers.py`

- [ ] **Step 1: Write failing command and formatter tests**

Add command tests that seed the stream summary and assert two messages:

```python
assert outputs == [
    "Stream Race Stats 🏁 Races: 5 total / 3 completed / 1 pending / 1 skipped 🏆 Winners: 1️⃣ Alice #1 2️⃣ Dan #2 3️⃣ Alice #1",
    "Stream Leaders 🏆 Drivers: Alice 2W / Dan 1W 🚗 Cars: #1 2W / #2 1W 🎯 Unique winners: 2",
]
```

Add an empty output test:

```python
assert outputs == [
    "Stream Race Stats 🏁 Races: 0 total / 0 completed / 0 pending / 0 skipped 🏆 Winners: none"
]
```

Add helper tests for local noon cutoff:

```python
assert trackracerbot.stream_race_stats_cutoff(
    datetime(2026, 6, 5, 13, 0, tzinfo=timezone.utc),
    ZoneInfo("America/New_York"),
) == datetime(2026, 6, 5, 12, 0, tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
```

And before-noon previous day behavior.

- [ ] **Step 2: Run failing command tests**

Run:

```powershell
.\.venv-codex\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py tests\test_trackracerbot_helpers.py -k "stream_race_stats or streamracestats" -v
```

Expected: fail because helpers and command do not exist.

- [ ] **Step 3: Implement command helpers and handler**

Add:

- `COMMAND_STREAM_RACE_STATS = "stream_race_stats"`
- `STREAM_RACE_STATS_COMMAND = "!streamracestats"`
- `is_stream_race_stats_message()`
- command classification before entry commands
- `stream_race_stats_cutoff(now_utc, local_timezone)`
- `build_stream_race_stats_messages(summary)`

Use `datetime.now(timezone.utc).astimezone()` for the local timezone at runtime. Format the cutoff as ISO UTC for `race_history.get_stream_race_summary()`.

- [ ] **Step 4: Run command tests**

Run:

```powershell
.\.venv-codex\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py tests\test_trackracerbot_helpers.py -k "stream_race_stats or streamracestats" -v
```

Expected: pass.

### Task 3: Discovery, Fixtures, and Verification

**Files:**
- Modify: `trackracerbot.py`
- Modify: `tests/fixtures/twitch/all_commands.jsonl`
- Modify: `tests/test_twitch_fixture_capture.py`
- Modify: `README.md`
- Modify: `BOT_DOCUMENTATION.md`

- [ ] **Step 1: Add command to help, fixtures, and docs**

Update `!commands` output to include `!streamracestats`.

Add fixture case:

```json
{"case":"streamracestats_empty","source":"twitch","author":"example_user","message":"!streamracestats","classification":"stream_race_stats","is_mod":false,"bot_outputs":["Stream Race Stats 🏁 Races: 0 total / 0 completed / 0 pending / 0 skipped 🏆 Winners: none"]}
```

Add viewer command rows to `README.md` and `BOT_DOCUMENTATION.md`.

- [ ] **Step 2: Run full verification**

Run:

```powershell
.\.venv-codex\Scripts\python.exe -m pytest -v
```

Run:

```powershell
& 'C:\Users\loony\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/entries_widget_paging.test.js
```

Run:

```powershell
git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
```

Expected: Python tests pass, Node widget test exits 0, and the IPv4 scan only reports existing documented local addresses.

## Self-Review

Spec coverage: the plan covers public command routing, local noon cutoff, one/two message behavior, approved message labels, no "since noon" output, counts, winners, stream leaders, fixtures, docs, and verification.

Placeholder scan: no placeholders or deferred implementation requirements remain.

Type consistency: helper names are `get_stream_race_summary`, `stream_race_stats_cutoff`, and `build_stream_race_stats_messages`; command classification is `stream_race_stats`.
