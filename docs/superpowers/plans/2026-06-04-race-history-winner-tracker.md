# Race History Winner Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable race records, winner recording, leaderboard, stats, and latest-winner export for treadmill races.

**Architecture:** Add a focused SQLite module, `race_history.py`, and keep bot orchestration in `trackracerbot.py`. Race records are created on mod `!start`; winner/stat commands query or mutate the latest stored race through the history module.

**Tech Stack:** Python 3.12, stdlib `sqlite3`, existing `pytest` and `pytest-asyncio`, existing Node widget test.

---

## File Structure

- Create `race_history.py`: SQLite schema, data-access API, stats queries, and lookup over stored race entries.
- Create `tests/test_race_history.py`: unit tests for the SQLite module with temporary DB files.
- Modify `trackracerbot.py`: command constants/helpers, race DB path, wall-clock submission window state, response formatting, `handle_message()` wiring, and WebSocket latest winner response.
- Modify `tests/test_trackracerbot_helpers.py`: pure command detection and response formatting tests.
- Modify `tests/test_twitch_fixture_capture.py`: async command flow tests using temp DB paths.
- Modify `tests/fixtures/twitch/all_commands.jsonl`: add coverage for new command classifications.
- Modify `.gitignore`: ignore generated race-history DB files.
- Modify `BOT_DOCUMENTATION.md`: document new commands and `RACE_HISTORY_DB`.

## Shared Implementation Notes

- Use exact-or-space command matching for all new commands:

```python
def is_exact_or_command_with_args(message: str, command: str) -> bool:
    message_lower = message.lower()
    return message_lower == command or message_lower.startswith(command + " ")
```

- Normalize usernames with the existing behavior:

```python
def normalize_entry_lookup_name(search_text: str) -> str:
    return search_text.strip().lstrip("@").lower()
```

- Use ISO-8601 UTC timestamps:

```python
from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
```

- Keep `time.monotonic()` only for elapsed submission stats and idle reminders.
- Before every commit, run the AGENTS IPv4 scan:

```powershell
git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
```

Expected known matches only: `AGENTS.md` and `BOT_DOCUMENTATION.md`.

---

### Task 1: SQLite Race History Schema

**Files:**
- Create: `race_history.py`
- Create: `tests/test_race_history.py`

- [ ] **Step 1: Write failing schema and race creation tests**

Add `tests/test_race_history.py`:

```python
import sqlite3

import race_history


def test_initialize_database_creates_tables(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"

    race_history.initialize_database(str(db_path))

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {"races", "race_entries"} <= table_names


def test_start_race_stores_entry_snapshot_with_display_numbers(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.initialize_database(str(db_path))

    race_id = race_history.start_race(
        str(db_path),
        entries=["racer_one"] + [f"racer_{index}" for index in range(2, 30)],
        started_at_utc="2026-06-04T20:00:00+00:00",
        entries_opened_at_utc="2026-06-04T19:50:00+00:00",
        entries_closed_at_utc="2026-06-04T20:00:00+00:00",
        created_by="example_mod",
    )

    race = race_history.get_latest_race(str(db_path))
    entries = race_history.get_race_entries(str(db_path), race_id)

    assert race["id"] == race_id
    assert race["status"] == race_history.STATUS_PENDING
    assert race["started_at_utc"] == "2026-06-04T20:00:00+00:00"
    assert race["entries_opened_at_utc"] == "2026-06-04T19:50:00+00:00"
    assert race["entries_closed_at_utc"] == "2026-06-04T20:00:00+00:00"
    assert race["created_by"] == "example_mod"
    assert entries[0]["name"] == "racer_one"
    assert entries[0]["position"] == 1
    assert entries[0]["display_number"] == 1
    assert entries[28]["position"] == 29
    assert entries[28]["display_number"] == 69
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_race_history.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'race_history'`.

- [ ] **Step 3: Implement schema and race creation**

Create `race_history.py`:

```python
import sqlite3
from datetime import datetime, timezone

STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_UNKNOWN = "unknown"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_database(db_path: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            create table if not exists races (
                id integer primary key,
                started_at_utc text not null,
                ended_at_utc text,
                entries_opened_at_utc text,
                entries_closed_at_utc text,
                status text not null,
                winner_entry_id integer,
                winner_name text,
                created_by text,
                updated_at_utc text not null
            )
            """
        )
        connection.execute(
            """
            create table if not exists race_entries (
                id integer primary key,
                race_id integer not null,
                position integer not null,
                display_number integer not null,
                name text not null,
                normalized_name text not null,
                foreign key (race_id) references races(id)
            )
            """
        )
        connection.execute(
            "create index if not exists idx_race_entries_race_id on race_entries(race_id)"
        )
        connection.execute(
            "create index if not exists idx_race_entries_normalized_name on race_entries(normalized_name)"
        )


def display_car_number(position: int) -> int:
    if position == 29:
        return 69
    return position


def normalize_name(name: str) -> str:
    return name.strip().lstrip("@").lower()


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def start_race(
    db_path: str,
    entries: list[str],
    started_at_utc: str | None = None,
    entries_opened_at_utc: str | None = None,
    entries_closed_at_utc: str | None = None,
    created_by: str | None = None,
) -> int:
    initialize_database(db_path)
    timestamp = started_at_utc or utc_now_iso()
    with connect(db_path) as connection:
        cursor = connection.execute(
            """
            insert into races (
                started_at_utc,
                ended_at_utc,
                entries_opened_at_utc,
                entries_closed_at_utc,
                status,
                winner_entry_id,
                winner_name,
                created_by,
                updated_at_utc
            )
            values (?, null, ?, ?, ?, null, null, ?, ?)
            """,
            (
                timestamp,
                entries_opened_at_utc,
                entries_closed_at_utc,
                STATUS_PENDING,
                created_by,
                timestamp,
            ),
        )
        race_id = int(cursor.lastrowid)
        connection.executemany(
            """
            insert into race_entries (
                race_id,
                position,
                display_number,
                name,
                normalized_name
            )
            values (?, ?, ?, ?, ?)
            """,
            [
                (
                    race_id,
                    position,
                    display_car_number(position),
                    name,
                    normalize_name(name),
                )
                for position, name in enumerate(entries, start=1)
            ],
        )
    return race_id


def get_latest_race(db_path: str) -> dict | None:
    initialize_database(db_path)
    with connect(db_path) as connection:
        row = connection.execute(
            "select * from races order by id desc limit 1"
        ).fetchone()
    return row_to_dict(row) if row is not None else None


def get_race_entries(db_path: str, race_id: int) -> list[dict]:
    initialize_database(db_path)
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            select * from race_entries
            where race_id = ?
            order by position
            """,
            (race_id,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_race_history.py -v
```

Expected: `2 passed`.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
git add race_history.py tests/test_race_history.py
git commit -m "Add race history storage schema"
```

Expected: IPv4 scan has only the known documented matches, then commit succeeds.

---

### Task 2: Race History Winner, Correction, Leaderboard, and Stats API

**Files:**
- Modify: `race_history.py`
- Modify: `tests/test_race_history.py`

- [ ] **Step 1: Write failing winner/stat tests**

Append to `tests/test_race_history.py`:

```python
def test_complete_latest_pending_race_records_winner_and_stats(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(
        str(db_path),
        ["RacerOne", "RacerTwo"],
        started_at_utc="2026-06-04T20:00:00+00:00",
    )

    result = race_history.complete_latest_pending_race(
        str(db_path),
        winner_query="2",
        ended_at_utc="2026-06-04T20:05:00+00:00",
    )

    assert result["status"] == race_history.STATUS_COMPLETED
    assert result["winner_name"] == "RacerTwo"
    assert result["stats"] == {
        "name": "RacerTwo",
        "wins": 1,
        "total_races": 1,
        "win_percentage": 100.0,
    }


def test_set_latest_race_winner_can_correct_completed_race(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["RacerOne", "RacerTwo"])
    race_history.complete_latest_pending_race(str(db_path), "RacerOne")

    result = race_history.set_latest_race_result(str(db_path), "RacerTwo")

    assert result["status"] == race_history.STATUS_COMPLETED
    assert result["winner_name"] == "RacerTwo"
    assert race_history.get_racer_stats(str(db_path), "RacerOne")["wins"] == 0
    assert race_history.get_racer_stats(str(db_path), "RacerTwo")["wins"] == 1


def test_set_latest_race_result_supports_skipped_and_unknown(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["RacerOne"])

    skipped = race_history.set_latest_race_result(str(db_path), "skipped")
    unknown = race_history.set_latest_race_result(str(db_path), "unknown")

    assert skipped["status"] == race_history.STATUS_SKIPPED
    assert skipped["winner_name"] is None
    assert unknown["status"] == race_history.STATUS_UNKNOWN
    assert unknown["winner_name"] is None
    assert race_history.get_racer_stats(str(db_path), "RacerOne") == {
        "name": "RacerOne",
        "wins": 0,
        "total_races": 1,
        "win_percentage": 0.0,
    }


def test_leaderboard_orders_by_wins_then_name(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    for winner in ["Beta", "Alpha", "Beta"]:
        race_history.start_race(str(db_path), ["Alpha", "Beta"])
        race_history.complete_latest_pending_race(str(db_path), winner)

    assert race_history.get_leaderboard(str(db_path), limit=5) == [
        {"name": "Beta", "wins": 2, "total_races": 3, "win_percentage": 66.7},
        {"name": "Alpha", "wins": 1, "total_races": 3, "win_percentage": 33.3},
    ]


def test_pending_race_blocks_next_start_when_snapshot_differs(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["RacerOne"])

    assert race_history.latest_pending_race_matches_entries(
        str(db_path), ["RacerTwo"]
    ) is False
    assert race_history.latest_pending_race_matches_entries(
        str(db_path), ["RacerOne"]
    ) is True
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_race_history.py -v
```

Expected: fail because `complete_latest_pending_race`, `set_latest_race_result`, `get_racer_stats`, `get_leaderboard`, and `latest_pending_race_matches_entries` are undefined.

- [ ] **Step 3: Implement winner/stat API**

Append to `race_history.py`:

```python
def find_entry_by_display_number(entries: list[dict], display_number: int) -> dict | None:
    for entry in entries:
        if int(entry["display_number"]) == display_number:
            return entry
    return None


def find_entry_by_name(entries: list[dict], search_text: str) -> dict | None:
    normalized_search = normalize_name(search_text)
    for entry in entries:
        if entry["normalized_name"] == normalized_search:
            return entry
    return None


def find_entry(entries: list[dict], query: str) -> dict | None:
    stripped = query.strip()
    if stripped.isdigit():
        return find_entry_by_display_number(entries, int(stripped))
    return find_entry_by_name(entries, stripped)


def get_latest_pending_race(db_path: str) -> dict | None:
    initialize_database(db_path)
    with connect(db_path) as connection:
        row = connection.execute(
            """
            select * from races
            where status = ?
            order by id desc
            limit 1
            """,
            (STATUS_PENDING,),
        ).fetchone()
    return row_to_dict(row) if row is not None else None


def latest_pending_race_matches_entries(db_path: str, entries: list[str]) -> bool:
    latest_pending = get_latest_pending_race(db_path)
    if latest_pending is None:
        return False
    stored_entries = get_race_entries(db_path, latest_pending["id"])
    stored_names = [entry["name"] for entry in stored_entries]
    return stored_names == list(entries)


def delete_race(db_path: str, race_id: int) -> None:
    initialize_database(db_path)
    with connect(db_path) as connection:
        connection.execute("delete from race_entries where race_id = ?", (race_id,))
        connection.execute("delete from races where id = ?", (race_id,))


def get_racer_stats(db_path: str, name: str) -> dict:
    initialize_database(db_path)
    normalized_name = normalize_name(name)
    with connect(db_path) as connection:
        latest_name_row = connection.execute(
            """
            select name from race_entries
            where normalized_name = ?
            order by race_id desc, position
            limit 1
            """,
            (normalized_name,),
        ).fetchone()
        total_races = connection.execute(
            """
            select count(distinct race_id)
            from race_entries
            where normalized_name = ?
            """,
            (normalized_name,),
        ).fetchone()[0]
        wins = connection.execute(
            """
            select count(*)
            from races
            where status = ?
              and winner_name is not null
              and lower(winner_name) = ?
            """,
            (STATUS_COMPLETED, normalized_name),
        ).fetchone()[0]

    display_name = latest_name_row["name"] if latest_name_row is not None else name.strip().lstrip("@")
    win_percentage = round((wins / total_races * 100) if total_races else 0.0, 1)
    return {
        "name": display_name,
        "wins": int(wins),
        "total_races": int(total_races),
        "win_percentage": win_percentage,
    }


def update_race_result(
    db_path: str,
    race: dict,
    status: str,
    winner_entry: dict | None = None,
    ended_at_utc: str | None = None,
) -> dict:
    timestamp = ended_at_utc or utc_now_iso()
    winner_entry_id = winner_entry["id"] if winner_entry is not None else None
    winner_name = winner_entry["name"] if winner_entry is not None else None
    with connect(db_path) as connection:
        connection.execute(
            """
            update races
            set status = ?,
                winner_entry_id = ?,
                winner_name = ?,
                ended_at_utc = ?,
                updated_at_utc = ?
            where id = ?
            """,
            (status, winner_entry_id, winner_name, timestamp, timestamp, race["id"]),
        )
    updated = get_latest_race(db_path)
    stats = get_racer_stats(db_path, winner_name) if winner_name is not None else None
    return {"race": updated, "status": status, "winner_name": winner_name, "stats": stats}


def complete_latest_pending_race(
    db_path: str,
    winner_query: str,
    ended_at_utc: str | None = None,
) -> dict | None:
    race = get_latest_pending_race(db_path)
    if race is None:
        return None
    entries = get_race_entries(db_path, race["id"])
    winner_entry = find_entry(entries, winner_query)
    if winner_entry is None:
        return {"error": "winner_not_found", "query": winner_query}
    return update_race_result(
        db_path,
        race,
        STATUS_COMPLETED,
        winner_entry=winner_entry,
        ended_at_utc=ended_at_utc,
    )


def set_latest_race_result(
    db_path: str,
    result_query: str,
    ended_at_utc: str | None = None,
) -> dict | None:
    race = get_latest_race(db_path)
    if race is None:
        return None
    normalized_query = normalize_name(result_query)
    if normalized_query == STATUS_SKIPPED:
        return update_race_result(db_path, race, STATUS_SKIPPED, ended_at_utc=ended_at_utc)
    if normalized_query == STATUS_UNKNOWN:
        return update_race_result(db_path, race, STATUS_UNKNOWN, ended_at_utc=ended_at_utc)
    entries = get_race_entries(db_path, race["id"])
    winner_entry = find_entry(entries, result_query)
    if winner_entry is None:
        return {"error": "winner_not_found", "query": result_query}
    return update_race_result(
        db_path,
        race,
        STATUS_COMPLETED,
        winner_entry=winner_entry,
        ended_at_utc=ended_at_utc,
    )


def get_leaderboard(db_path: str, limit: int = 5) -> list[dict]:
    initialize_database(db_path)
    with connect(db_path) as connection:
        winner_rows = connection.execute(
            """
            select lower(winner_name) as normalized_name, max(winner_name) as name, count(*) as wins
            from races
            where status = ? and winner_name is not null
            group by lower(winner_name)
            order by wins desc, normalized_name asc
            limit ?
            """,
            (STATUS_COMPLETED, limit),
        ).fetchall()

    leaderboard = []
    for row in winner_rows:
        stats = get_racer_stats(db_path, row["normalized_name"])
        stats["name"] = row["name"]
        leaderboard.append(stats)
    return leaderboard
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_race_history.py -v
```

Expected: all `tests/test_race_history.py` tests pass.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
git add race_history.py tests/test_race_history.py
git commit -m "Add race winner and stats queries"
```

Expected: IPv4 scan has only the known documented matches, then commit succeeds.

---

### Task 3: Bot Command Detection and Response Formatting

**Files:**
- Modify: `trackracerbot.py`
- Modify: `tests/test_trackracerbot_helpers.py`

- [ ] **Step 1: Write failing helper tests**

Append to `tests/test_trackracerbot_helpers.py`:

```python
def test_new_race_history_commands_use_exact_or_space_matching():
    assert trackracerbot.is_winner_message("!winner")
    assert trackracerbot.is_winner_message("!winner 12")
    assert not trackracerbot.is_winner_message("!winnerboard")
    assert trackracerbot.is_set_last_winner_message("!setlastwinner racer")
    assert not trackracerbot.is_set_last_winner_message("!setlastwinnerboard")
    assert trackracerbot.is_leaderboard_message("!leaderboard")
    assert not trackracerbot.is_leaderboard_message("!leaderboards")
    assert trackracerbot.is_stats_message("!stats")
    assert trackracerbot.is_stats_message("!stats racer")
    assert not trackracerbot.is_stats_message("!statsboard")


def test_classify_message_includes_race_history_commands():
    assert trackracerbot.classify_message("!winner") == trackracerbot.COMMAND_WINNER
    assert trackracerbot.classify_message("!winner racer") == trackracerbot.COMMAND_WINNER
    assert (
        trackracerbot.classify_message("!setlastwinner racer")
        == trackracerbot.COMMAND_SET_LAST_WINNER
    )
    assert (
        trackracerbot.classify_message("!leaderboard")
        == trackracerbot.COMMAND_LEADERBOARD
    )
    assert trackracerbot.classify_message("!stats") == trackracerbot.COMMAND_STATS


def test_race_stat_response_formatting_is_short():
    assert trackracerbot.format_racer_stats(
        {"name": "RacerOne", "wins": 3, "total_races": 12, "win_percentage": 25.0}
    ) == "RacerOne: 3W / 12R / 25.0%."


def test_leaderboard_response_formatting_limits_to_top_five():
    leaderboard = [
        {"name": f"racer_{index}", "wins": 6 - index, "total_races": 10, "win_percentage": 50.0}
        for index in range(1, 7)
    ]

    assert trackracerbot.build_leaderboard_response(leaderboard) == (
        "Top winners: 1. racer_1 5W/10R 50.0%; "
        "2. racer_2 4W/10R 50.0%; "
        "3. racer_3 3W/10R 50.0%; "
        "4. racer_4 2W/10R 50.0%; "
        "5. racer_5 1W/10R 50.0%."
    )
```

- [ ] **Step 2: Run helper tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_trackracerbot_helpers.py -v
```

Expected: fail because new command helpers and formatting helpers are undefined.

- [ ] **Step 3: Implement command constants, helpers, and formatters**

In `trackracerbot.py`, add `import race_history` near existing imports.

Add constants near existing command labels:

```python
COMMAND_WINNER = "winner"
COMMAND_SET_LAST_WINNER = "set_last_winner"
COMMAND_LEADERBOARD = "leaderboard"
COMMAND_STATS = "stats"

WINNER_COMMAND = "!winner"
SET_LAST_WINNER_COMMAND = "!setlastwinner"
LEADERBOARD_COMMAND = "!leaderboard"
STATS_COMMAND = "!stats"
```

Add DB path setup near `bot_state_file_abs`:

```python
race_history_db = os.getenv("RACE_HISTORY_DB")
if race_history_db is None:
    race_history_db = os.path.join(os.path.dirname(entry_file_abs), "race-history.sqlite3")
race_history_db_abs = os.path.abspath(race_history_db)
```

Add helper functions near current command detection helpers:

```python
def is_exact_or_command_with_args(message: str, command: str) -> bool:
    message_lower = message.lower()
    return message_lower == command or message_lower.startswith(command + " ")


def is_winner_message(message: str) -> bool:
    return is_exact_or_command_with_args(message, WINNER_COMMAND)


def is_set_last_winner_message(message: str) -> bool:
    return is_exact_or_command_with_args(message, SET_LAST_WINNER_COMMAND)


def is_leaderboard_message(message: str) -> bool:
    return is_exact_or_command_with_args(message, LEADERBOARD_COMMAND)


def is_stats_message(message: str) -> bool:
    return is_exact_or_command_with_args(message, STATS_COMMAND)
```

Update `classify_message()` after `!entry` lookup and before entry commands:

```python
    if is_winner_message(message):
        return COMMAND_WINNER
    if is_set_last_winner_message(message):
        return COMMAND_SET_LAST_WINNER
    if is_leaderboard_message(message):
        return COMMAND_LEADERBOARD
    if is_stats_message(message):
        return COMMAND_STATS
```

Add response formatters near existing response builders:

```python
def format_racer_stats(stats: dict) -> str:
    return (
        f"{stats['name']}: {stats['wins']}W / "
        f"{stats['total_races']}R / {stats['win_percentage']:.1f}%."
    )


def format_inline_racer_stats(stats: dict) -> str:
    return f"{stats['wins']}W / {stats['total_races']}R / {stats['win_percentage']:.1f}%"


def build_leaderboard_response(leaderboard: list[dict]) -> str:
    if not leaderboard:
        return "No completed winners yet."
    parts = []
    for index, stats in enumerate(leaderboard[:5], start=1):
        parts.append(
            f"{index}. {stats['name']} "
            f"{stats['wins']}W/{stats['total_races']}R "
            f"{stats['win_percentage']:.1f}%"
        )
    return "Top winners: " + "; ".join(parts) + "."
```

- [ ] **Step 4: Run helper tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_trackracerbot_helpers.py -v
```

Expected: helper tests pass.

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
git add trackracerbot.py tests/test_trackracerbot_helpers.py
git commit -m "Add race history command helpers"
```

Expected: IPv4 scan has only the known documented matches, then commit succeeds.

---

### Task 4: Start Lifecycle Integration

**Files:**
- Modify: `trackracerbot.py`
- Modify: `tests/test_twitch_fixture_capture.py`

- [ ] **Step 1: Write failing start lifecycle tests**

Add tests to `tests/test_twitch_fixture_capture.py` near existing `!start` tests:

```python
@pytest.mark.asyncio
async def test_start_with_no_entries_is_blocked(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))

    await trackracerbot.handle_message(
        "!start",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    assert outputs == ["No entries to start."]
    assert trackracerbot.race_history.get_latest_race(
        trackracerbot.race_history_db_abs
    ) is None


@pytest.mark.asyncio
async def test_start_creates_pending_race_snapshot(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(tmp_path / "bot-state.json"))
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))
    trackracerbot.entry_queue.extend(["RacerONE", "RACERTwo"])

    await trackracerbot.handle_message(
        "!start",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    latest = trackracerbot.race_history.get_latest_race(trackracerbot.race_history_db_abs)
    entries = trackracerbot.race_history.get_race_entries(
        trackracerbot.race_history_db_abs,
        latest["id"],
    )
    assert outputs == ["Starting grid locked: racerone, racertwo"]
    assert latest["status"] == trackracerbot.race_history.STATUS_PENDING
    assert [entry["name"] for entry in entries] == ["RacerONE", "RACERTwo"]


@pytest.mark.asyncio
async def test_start_same_lineup_replaces_pending_race(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(tmp_path / "bot-state.json"))
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))
    trackracerbot.entry_queue.extend(["RacerONE", "RACERTwo"])

    await trackracerbot.handle_message("!start", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True))
    first_race = trackracerbot.race_history.get_latest_race(trackracerbot.race_history_db_abs)
    await trackracerbot.handle_message("!start", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True))
    second_race = trackracerbot.race_history.get_latest_race(trackracerbot.race_history_db_abs)

    assert outputs == [
        "Starting grid locked: racerone, racertwo",
        "Rolling out with: racerone, racertwo",
    ]
    assert second_race["id"] != first_race["id"]


@pytest.mark.asyncio
async def test_start_changed_lineup_requires_previous_winner(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(tmp_path / "bot-state.json"))
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))
    trackracerbot.entry_queue.extend(["RacerONE"])

    await trackracerbot.handle_message("!start", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True))
    trackracerbot.entry_queue.clear()
    trackracerbot.entry_queue.extend(["DifferentRacer"])
    await trackracerbot.handle_message("!start", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True))

    assert outputs[-1] == (
        "Record the last winner first: !winner {number or name}. "
        "Use !setlastwinner skipped if there was no winner."
    )
```

- [ ] **Step 2: Run targeted tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py -k "start" -v
```

Expected: new tests fail because `!start` does not use race history yet.

- [ ] **Step 3: Implement start lifecycle wiring**

In `trackracerbot.py`, add wall-clock submission window state near `submission_stats`:

```python
submission_window = {
    "entries_opened_at_utc": None,
    "entries_closed_at_utc": None,
}
```

Update `write_registration_state()` JSON object:

```python
{
    "registration_open": registration_open,
    "submission_stats": submission_stats,
    "submission_window": submission_window,
}
```

Update `load_registration_state()` after `submission_stats` loading:

```python
loaded_submission_window = state.get("submission_window", {})
if isinstance(loaded_submission_window, dict):
    submission_window["entries_opened_at_utc"] = loaded_submission_window.get(
        "entries_opened_at_utc"
    )
    submission_window["entries_closed_at_utc"] = loaded_submission_window.get(
        "entries_closed_at_utc"
    )
```

Add helpers near submission stat helpers:

```python
def mark_entries_opened(opened_at_utc: str = None) -> None:
    submission_window["entries_opened_at_utc"] = opened_at_utc or race_history.utc_now_iso()
    submission_window["entries_closed_at_utc"] = None
    write_registration_state()


def mark_entries_closed(closed_at_utc: str = None) -> None:
    submission_window["entries_closed_at_utc"] = closed_at_utc or race_history.utc_now_iso()
    write_registration_state()
```

Update `COMMAND_START` block in `handle_message()`:

```python
    elif command == COMMAND_START and is_mod:
        lineup_names = list(itertools.islice(entry_queue, 0, MAX_ENTRIES))
        if not lineup_names:
            await respond("No entries to start.")
            write_chat_capture_record(
                build_twitch_capture_record(
                    message=message,
                    author=author,
                    command=command,
                    is_mod=is_mod,
                    bot_outputs=capture_outputs,
                    twitch_message=twitch_message,
                )
            )
            return

        latest_pending = race_history.get_latest_pending_race(race_history_db_abs)
        if latest_pending is not None:
            if race_history.latest_pending_race_matches_entries(
                race_history_db_abs, lineup_names
            ):
                race_history.delete_race(race_history_db_abs, latest_pending["id"])
            else:
                await respond(
                    "Record the last winner first: !winner {number or name}. "
                    "Use !setlastwinner skipped if there was no winner."
                )
                write_chat_capture_record(
                    build_twitch_capture_record(
                        message=message,
                        author=author,
                        command=command,
                        is_mod=is_mod,
                        bot_outputs=capture_outputs,
                        twitch_message=twitch_message,
                    )
                )
                return

        mark_entries_closed()
        race_history.start_race(
            race_history_db_abs,
            lineup_names,
            entries_opened_at_utc=submission_window["entries_opened_at_utc"],
            entries_closed_at_utc=submission_window["entries_closed_at_utc"],
            created_by=author,
        )
        await respond(build_start_response(lineup_names, next(start_response_counter)))
        set_registration_open(False)
```

Update `COMMAND_OPEN_ENTRIES` and `COMMAND_CLEAR_ENTRIES` blocks:

```python
        mark_entries_opened()
```

Add this call after successful `set_registration_open(True)` in both branches.

Update `COMMAND_CLOSE_ENTRIES` block:

```python
        mark_entries_closed()
```

Add this call after `set_registration_open(False)`.

- [ ] **Step 4: Run start lifecycle tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py -k "start" -v
```

Expected: targeted start tests pass.

- [ ] **Step 5: Commit Task 4**

Run:

```powershell
git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
git add trackracerbot.py tests/test_twitch_fixture_capture.py
git commit -m "Create race records on start"
```

Expected: IPv4 scan has only the known documented matches, then commit succeeds.

---

### Task 5: Winner and Set-Last-Winner Command Integration

**Files:**
- Modify: `trackracerbot.py`
- Modify: `tests/test_twitch_fixture_capture.py`

- [ ] **Step 1: Write failing winner command tests**

Append to `tests/test_twitch_fixture_capture.py`:

```python
@pytest.mark.asyncio
async def test_winner_without_args_reports_pending_latest_race(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))
    trackracerbot.race_history.start_race(trackracerbot.race_history_db_abs, ["RacerOne"])

    await trackracerbot.handle_message(
        "!winner",
        "viewer",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == ["Last race has no winner recorded yet."]


@pytest.mark.asyncio
async def test_mod_winner_records_latest_pending_race(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))
    trackracerbot.race_history.start_race(
        trackracerbot.race_history_db_abs,
        ["RacerOne", "RacerTwo"],
    )

    await trackracerbot.handle_message(
        "!winner 2",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    assert outputs == ["Winner recorded: RacerTwo. 1W / 1R / 100.0%."]


@pytest.mark.asyncio
async def test_non_mod_winner_with_args_does_not_mutate_history(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))
    trackracerbot.race_history.start_race(trackracerbot.race_history_db_abs, ["RacerOne"])

    await trackracerbot.handle_message(
        "!winner RacerOne",
        "viewer",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    latest = trackracerbot.race_history.get_latest_race(trackracerbot.race_history_db_abs)
    assert outputs == []
    assert latest["status"] == trackracerbot.race_history.STATUS_PENDING


@pytest.mark.asyncio
async def test_set_last_winner_supports_skipped_unknown_and_correction(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))
    trackracerbot.race_history.start_race(trackracerbot.race_history_db_abs, ["RacerOne", "RacerTwo"])

    await trackracerbot.handle_message("!setlastwinner skipped", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True))
    await trackracerbot.handle_message("!setlastwinner unknown", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True))
    await trackracerbot.handle_message("!setlastwinner RacerTwo", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True))

    assert outputs == [
        "Last race marked skipped.",
        "Last race winner marked unknown.",
        "Last winner updated: RacerTwo. 1W / 1R / 100.0%.",
    ]
```

- [ ] **Step 2: Run winner tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py -k "winner" -v
```

Expected: new tests fail because command handling is not wired.

- [ ] **Step 3: Add latest-winner response helpers**

Add to `trackracerbot.py` near response builders:

```python
def build_latest_winner_response(db_path: str) -> str:
    latest = race_history.get_latest_race(db_path)
    if latest is None:
        return "No races recorded yet."
    if latest["status"] == race_history.STATUS_PENDING:
        return "Last race has no winner recorded yet."
    if latest["status"] == race_history.STATUS_SKIPPED:
        return "Last race was skipped."
    if latest["status"] == race_history.STATUS_UNKNOWN:
        return "Last race winner is unknown."
    stats = race_history.get_racer_stats(db_path, latest["winner_name"])
    return f"Last winner: {latest['winner_name']}. {format_inline_racer_stats(stats)}."


def build_winner_recorded_response(prefix: str, result: dict) -> str:
    stats = result["stats"]
    return f"{prefix}: {result['winner_name']}. {format_inline_racer_stats(stats)}."
```

- [ ] **Step 4: Wire `!winner` and `!setlastwinner` in `handle_message()`**

Add before entry command handling:

```python
    elif command == COMMAND_WINNER:
        winner_query = message[len(WINNER_COMMAND):].strip()
        if not winner_query:
            await respond(build_latest_winner_response(race_history_db_abs))
        elif is_mod:
            result = race_history.complete_latest_pending_race(
                race_history_db_abs,
                winner_query,
            )
            if result is None:
                await respond("No pending race to record a winner for.")
            elif result.get("error") == "winner_not_found":
                await respond(f"No entry found for {winner_query}.")
            else:
                await respond(build_winner_recorded_response("Winner recorded", result))

    elif command == COMMAND_SET_LAST_WINNER and is_mod:
        result_query = message[len(SET_LAST_WINNER_COMMAND):].strip()
        if not result_query:
            await respond("Usage: !setlastwinner {number, name, skipped, or unknown}")
        else:
            result = race_history.set_latest_race_result(
                race_history_db_abs,
                result_query,
            )
            if result is None:
                await respond("No races recorded yet.")
            elif result.get("error") == "winner_not_found":
                await respond(f"No entry found for {result_query}.")
            elif result["status"] == race_history.STATUS_SKIPPED:
                await respond("Last race marked skipped.")
            elif result["status"] == race_history.STATUS_UNKNOWN:
                await respond("Last race winner marked unknown.")
            else:
                await respond(build_winner_recorded_response("Last winner updated", result))
```

- [ ] **Step 5: Run winner tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py -k "winner" -v
```

Expected: winner tests pass.

- [ ] **Step 6: Commit Task 5**

Run:

```powershell
git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
git add trackracerbot.py tests/test_twitch_fixture_capture.py
git commit -m "Record race winners from chat commands"
```

Expected: IPv4 scan has only the known documented matches, then commit succeeds.

---

### Task 6: Leaderboard, Stats, Command Help, Fixtures, and WebSocket

**Files:**
- Modify: `trackracerbot.py`
- Modify: `tests/test_twitch_fixture_capture.py`
- Modify: `tests/fixtures/twitch/all_commands.jsonl`
- Modify: `BOT_DOCUMENTATION.md`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing leaderboard/stats/WebSocket tests**

Append to `tests/test_twitch_fixture_capture.py`:

```python
@pytest.mark.asyncio
async def test_leaderboard_and_stats_commands_report_race_history(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    db_path = str(tmp_path / "race-history.sqlite3")
    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", db_path)
    for winner in ["RacerTwo", "RacerTwo", "RacerOne"]:
        trackracerbot.race_history.start_race(db_path, ["RacerOne", "RacerTwo"])
        trackracerbot.race_history.complete_latest_pending_race(db_path, winner)

    await trackracerbot.handle_message("!leaderboard", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))
    await trackracerbot.handle_message("!stats RacerTwo", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))
    await trackracerbot.handle_message("!stats", "RacerOne", twitch_message=FakeTwitchMessage(is_mod=False))

    assert outputs == [
        "Top winners: 1. RacerTwo 2W/3R 66.7%; 2. RacerOne 1W/3R 33.3%.",
        "RacerTwo: 2W / 3R / 66.7%.",
        "RacerOne: 1W / 3R / 33.3%.",
    ]


def test_latest_winner_json_uses_race_history(tmp_path, monkeypatch):
    db_path = str(tmp_path / "race-history.sqlite3")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", db_path)
    trackracerbot.race_history.start_race(db_path, ["RacerOne"])
    trackracerbot.race_history.complete_latest_pending_race(db_path, "RacerOne")

    payload = trackracerbot.latest_winner_json()

    assert payload == {
        "status": "completed",
        "winner": "RacerOne",
        "stats": {
            "name": "RacerOne",
            "wins": 1,
            "total_races": 1,
            "win_percentage": 100.0,
        },
    }
```

- [ ] **Step 2: Run targeted tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py -k "leaderboard or stats or latest_winner" -v
```

Expected: fail because leaderboard/stats handlers and `latest_winner_json()` are undefined.

- [ ] **Step 3: Implement leaderboard, stats, help, and latest winner JSON**

Add response helper:

```python
def latest_winner_json() -> dict:
    latest = race_history.get_latest_race(race_history_db_abs)
    if latest is None:
        return {"status": "none", "winner": None, "stats": None}
    if latest["status"] != race_history.STATUS_COMPLETED:
        return {"status": latest["status"], "winner": None, "stats": None}
    stats = race_history.get_racer_stats(race_history_db_abs, latest["winner_name"])
    return {
        "status": latest["status"],
        "winner": latest["winner_name"],
        "stats": stats,
    }
```

Update `COMMAND_COMMANDS` branch:

```python
        commands_message = "Available commands: !play !entries !winner !leaderboard !stats"
        if is_mod:
            commands_message += (
                " // Mod Commands: !start !openentries !closeentries !clearentries "
                "!winner <number|name> !setlastwinner"
            )
```

Add handlers before entry command handling:

```python
    elif command == COMMAND_LEADERBOARD:
        await respond(
            build_leaderboard_response(
                race_history.get_leaderboard(race_history_db_abs, limit=5)
            )
        )

    elif command == COMMAND_STATS:
        stats_query = message[len(STATS_COMMAND):].strip() or author
        if stats_query.isdigit():
            latest = race_history.get_latest_race(race_history_db_abs)
            if latest is None:
                await respond(f"No racer found for car #{stats_query}.")
            else:
                entries = race_history.get_race_entries(race_history_db_abs, latest["id"])
                entry = race_history.find_entry_by_display_number(entries, int(stats_query))
                if entry is None:
                    await respond(f"No racer found for car #{stats_query}.")
                else:
                    stats = race_history.get_racer_stats(race_history_db_abs, entry["name"])
                    await respond(format_racer_stats(stats))
        else:
            stats = race_history.get_racer_stats(race_history_db_abs, stats_query)
            if stats["total_races"] == 0:
                await respond(f"No race stats found for {stats['name']}.")
            else:
                await respond(format_racer_stats(stats))
```

Update WebSocket handling:

```python
        elif msg == "latest_winner":
            socket_data = latest_winner_json()
```

- [ ] **Step 4: Update fixture replay cases**

Edit `tests/fixtures/twitch/all_commands.jsonl` to add cases:

```jsonl
{"case":"winner_read","source":"twitch","author":"example_user","message":"!winner","classification":"winner","is_mod":false,"bot_outputs":["No races recorded yet."]}
{"case":"leaderboard","source":"twitch","author":"example_user","message":"!leaderboard","classification":"leaderboard","is_mod":false,"bot_outputs":["No completed winners yet."]}
{"case":"stats_self","source":"twitch","author":"example_user","message":"!stats","classification":"stats","is_mod":false,"bot_outputs":["No race stats found for example_user."]}
```

If the replay helper needs temp DB isolation, update it to monkeypatch `race_history_db_abs` to `tmp_path / "race-history.sqlite3"` for every replayed case.

- [ ] **Step 5: Update `.gitignore`**

Add:

```text
race-history.sqlite3
race-history.sqlite3-*
```

- [ ] **Step 6: Update documentation**

In `BOT_DOCUMENTATION.md`, add user commands:

```markdown
| `!winner` | Shows the latest race winner or latest race winner status |
| `!leaderboard` | Shows the top 5 winners with compact stats |
| `!stats [name]` | Shows your stats, or another racer's stats when a name is provided |
```

Add moderator commands:

```markdown
| `!winner <number or name>` | Records the winner for the latest pending race |
| `!setlastwinner <number, name, skipped, or unknown>` | Corrects the latest race result |
```

Add environment variable:

```markdown
| `RACE_HISTORY_DB` | SQLite database path for durable race history (default: `race-history.sqlite3`) |
```

- [ ] **Step 7: Run targeted tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_twitch_fixture_capture.py -k "leaderboard or stats or latest_winner or replay" -v
```

Expected: targeted tests pass.

- [ ] **Step 8: Commit Task 6**

Run:

```powershell
git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
git add trackracerbot.py tests/test_twitch_fixture_capture.py tests/fixtures/twitch/all_commands.jsonl BOT_DOCUMENTATION.md .gitignore
git commit -m "Add race leaderboard stats and winner export"
```

Expected: IPv4 scan has only the known documented matches, then commit succeeds.

---

### Task 7: Full Verification and Polish

**Files:**
- Modify only files needed to fix verification failures discovered in this task.

- [ ] **Step 1: Run full Python test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: all Python tests pass.

- [ ] **Step 2: Run Node widget test**

Run:

```powershell
& 'C:\Users\loony\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests\entries_widget_paging.test.js
```

Expected: exit code `0`.

- [ ] **Step 3: Run IPv4 tracked-file scan**

Run:

```powershell
git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"
```

Expected known matches only: the existing local and bind-address references in `AGENTS.md` and `BOT_DOCUMENTATION.md`.

- [ ] **Step 4: Inspect working tree**

Run:

```powershell
git status --short
```

Expected: only intentional modified files, or clean if all task commits are complete.

- [ ] **Step 5: Commit any verification fixes**

If Step 1 or Step 2 required fixes, commit them:

```powershell
git add <fixed-files>
git commit -m "Polish race history winner tracker"
```

Expected: commit succeeds. If no fixes were required, skip this step.

---

## Self-Review

- Spec coverage:
  - Durable SQLite storage: Tasks 1 and 2.
  - Race record on `!start`: Task 4.
  - Empty start blocking: Task 4.
  - Same-lineup double-start override and changed-lineup refusal: Task 4.
  - `!winner` read/write and mod-only mutation: Task 5.
  - `!setlastwinner`: Task 5.
  - Leaderboard, stats, command help, WebSocket latest winner: Task 6.
  - Docs, fixture, `.gitignore`, full tests, IPv4 scan: Tasks 6 and 7.
- Placeholder scan: no red-flag placeholder wording or open-ended implementation steps.
- Type consistency: shared names are `race_history_db_abs`, `STATUS_PENDING`, `STATUS_COMPLETED`, `STATUS_SKIPPED`, `STATUS_UNKNOWN`, `get_latest_race`, `get_latest_pending_race`, `get_race_entries`, `complete_latest_pending_race`, `set_latest_race_result`, `get_racer_stats`, and `get_leaderboard`.
