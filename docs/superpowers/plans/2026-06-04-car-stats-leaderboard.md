# Car Stats Leaderboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add public `!carstats <number>` and `!carleaderboard` commands that aggregate historical race performance by display car number.

**Architecture:** Keep SQLite aggregation in `race_history.py`, matching existing racer stats helpers. Keep chat response formatting and command routing in `trackracerbot.py`, matching the current `!stats` and `!leaderboard` commands.

**Tech Stack:** Python, SQLite, pytest, existing Twitch fixture replay tests.

---

## File Structure

- Modify `race_history.py`: add `get_car_stats(db_path, display_number)` and `get_car_leaderboard(db_path, limit=5)`.
- Modify `trackracerbot.py`: add command constants, classification helpers, response builders, and command handlers.
- Modify `tests/test_race_history.py`: cover aggregate helper behavior.
- Modify `tests/test_twitch_fixture_capture.py`: cover public command responses and fixture replay.
- Modify `tests/fixtures/twitch/all_commands.jsonl`: add command fixture cases.
- Modify `README.md` and `BOT_DOCUMENTATION.md`: document both public commands.

### Task 1: Race History Aggregates

**Files:**
- Modify: `race_history.py`
- Test: `tests/test_race_history.py`

- [ ] **Step 1: Write failing helper tests**

Add tests that create races with repeated display car numbers, complete winners, and assert:

```python
def test_get_car_stats_reports_display_number_performance(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    start_race(str(db_path), ["Alice", "Bob", "Cara"])
    complete_latest_pending_race(str(db_path), "Bob")
    start_race(str(db_path), ["Dana", "Eli", "Fay"])
    complete_latest_pending_race(str(db_path), "Eli")
    start_race(str(db_path), ["Gus", "Hal", "Ivy"])
    complete_latest_pending_race(str(db_path), "Ivy")

    assert get_car_stats(str(db_path), 2) == {
        "display_number": 2,
        "wins": 2,
        "total_races": 3,
        "win_percentage": 66.7,
        "best_driver": "Bob",
        "best_driver_wins": 1,
        "last_win": "Eli",
    }
```

Also add:

```python
def test_get_car_leaderboard_ranks_by_wins_rate_and_number(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    start_race(str(db_path), ["A1", "B1", "C1"])
    complete_latest_pending_race(str(db_path), "B1")
    start_race(str(db_path), ["A2", "B2", "C2"])
    complete_latest_pending_race(str(db_path), "B2")
    start_race(str(db_path), ["A3", "B3", "C3"])
    complete_latest_pending_race(str(db_path), "C3")

    assert get_car_leaderboard(str(db_path), limit=2) == [
        {
            "display_number": 2,
            "wins": 2,
            "total_races": 3,
            "win_percentage": 66.7,
        },
        {
            "display_number": 3,
            "wins": 1,
            "total_races": 3,
            "win_percentage": 33.3,
        },
    ]
```

- [ ] **Step 2: Run failing tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_race_history.py -k "car_stats or car_leaderboard" -v`

Expected: fail because helper functions do not exist.

- [ ] **Step 3: Implement aggregate helpers**

Add SQLite queries that count appearances from `race_entries`, wins from completed `races.winner_entry_id`, best driver by win count, and last winner by most recent completed race.

- [ ] **Step 4: Run helper tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_race_history.py -k "car_stats or car_leaderboard" -v`

Expected: pass.

### Task 2: Chat Commands

**Files:**
- Modify: `trackracerbot.py`
- Test: `tests/test_twitch_fixture_capture.py`

- [ ] **Step 1: Write failing command tests**

Add tests that seed race history and assert:

```python
await trackracerbot.handle_message("!carstats 2", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))
assert outputs == ["Car #2: 2W / 3R / 66.7%. Best driver: Bob 1W. Last win: Eli."]
```

Add leaderboard and usage cases:

```python
await trackracerbot.handle_message("!carleaderboard", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))
assert outputs == ["Top cars: 1. #2 2W/3R 66.7%; 2. #3 1W/3R 33.3%."]

await trackracerbot.handle_message("!carstats", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))
assert outputs == ["Usage: !carstats <number>"]
```

- [ ] **Step 2: Run failing command tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py -k "carstats or carleaderboard" -v`

Expected: fail because commands are unknown.

- [ ] **Step 3: Implement command routing and formatting**

Add `COMMAND_CAR_STATS`, `COMMAND_CAR_LEADERBOARD`, `CAR_STATS_COMMAND`, and `CAR_LEADERBOARD_COMMAND`. Add classifiers using `is_exact_or_space_command` for `!carstats` and exact match for `!carleaderboard`. Add response builders:

```python
def build_car_stats_response(stats: dict | None, query: str) -> str:
    if not query.strip().isdecimal() or int(query) <= 0:
        return "Usage: !carstats <number>"
    display_number = int(query)
    if stats is None:
        return f"No races recorded for car #{display_number}."
    details = (
        f"Car #{stats['display_number']}: {stats['wins']}W / "
        f"{stats['total_races']}R / {stats['win_percentage']:.1f}%."
    )
    if stats["best_driver"] is not None:
        details += f" Best driver: {stats['best_driver']} {stats['best_driver_wins']}W."
    if stats["last_win"] is not None:
        details += f" Last win: {stats['last_win']}."
    return details
```

Add a top-five leaderboard builder matching the approved chat format.

- [ ] **Step 4: Run command tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py -k "carstats or carleaderboard" -v`

Expected: pass.

### Task 3: Command Discovery and Fixtures

**Files:**
- Modify: `trackracerbot.py`
- Modify: `tests/fixtures/twitch/all_commands.jsonl`
- Modify: `README.md`
- Modify: `BOT_DOCUMENTATION.md`

- [ ] **Step 1: Update help tests and fixture cases**

Update expected `!commands` output to include `!carstats !carleaderboard`.

Add JSONL fixture cases:

```json
{"case":"carstats_usage","source":"twitch","author":"example_user","message":"!carstats","classification":"car_stats","is_mod":false,"bot_outputs":["Usage: !carstats <number>"]}
{"case":"carleaderboard_empty","source":"twitch","author":"example_user","message":"!carleaderboard","classification":"car_leaderboard","is_mod":false,"bot_outputs":["No completed car winners yet."]}
```

- [ ] **Step 2: Update docs**

Add viewer command rows for `!carstats <number>` and `!carleaderboard` to `README.md` and `BOT_DOCUMENTATION.md`.

- [ ] **Step 3: Run full relevant tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_race_history.py tests\test_twitch_fixture_capture.py tests\test_trackracerbot_helpers.py -v`

Expected: pass.

- [ ] **Step 4: Run IP scan**

Run: `git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"`

Expected: only documented local bind addresses already allowed by `AGENTS.md`.

## Self-Review

Spec coverage: the plan covers both public commands, per-car aggregate semantics, leaderboard ranking, edge cases, docs, and tests.

Placeholder scan: no placeholders or deferred implementation requirements remain.

Type consistency: helper names are `get_car_stats`, `get_car_leaderboard`, command names are `COMMAND_CAR_STATS`, `COMMAND_CAR_LEADERBOARD`, `CAR_STATS_COMMAND`, and `CAR_LEADERBOARD_COMMAND`.
