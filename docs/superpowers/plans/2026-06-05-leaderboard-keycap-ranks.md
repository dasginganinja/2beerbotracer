# Leaderboard Keycap Ranks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace plain numeric rank labels in public leaderboard chat output with Unicode keycap rank markers.

**Architecture:** Keep this as a formatter-only change in `trackracerbot.py`. Add one shared helper for rank markers and use it in both existing leaderboard response builders.

**Tech Stack:** Python, pytest, existing Twitch command fixture tests.

---

## File Structure

- Modify `trackracerbot.py`: add `leaderboard_rank_marker(index: int) -> str` and update `build_leaderboard_response()` and `build_car_leaderboard_response()`.
- Modify `tests/test_trackracerbot_helpers.py`: assert the regular leaderboard formatter uses keycap ranks and no semicolons.
- Modify `tests/test_twitch_fixture_capture.py`: assert chat command output for `!leaderboard` and `!carleaderboard` uses keycap ranks.

### Task 1: Keycap Leaderboard Formatting

**Files:**
- Modify: `trackracerbot.py`
- Test: `tests/test_trackracerbot_helpers.py`
- Test: `tests/test_twitch_fixture_capture.py`

- [ ] **Step 1: Write failing formatter tests**

Update `tests/test_trackracerbot_helpers.py::test_leaderboard_response_formatting_limits_to_top_five` expected output to:

```python
assert trackracerbot.build_leaderboard_response(leaderboard) == (
    "Top winners: 1️⃣ racer_1 5W/10R 50.0% "
    "2️⃣ racer_2 4W/10R 40.0% "
    "3️⃣ racer_3 3W/10R 30.0% "
    "4️⃣ racer_4 2W/10R 20.0% "
    "5️⃣ racer_5 1W/10R 10.0%."
)
```

Update `tests/test_twitch_fixture_capture.py` expected regular leaderboard output to:

```python
"Top winners: 1️⃣ RacerTwo 2W/3R 66.7% 2️⃣ RacerOne 1W/3R 33.3%."
```

Update car leaderboard output to:

```python
"Top cars: 1️⃣ #2 2W/3R 66.7% 2️⃣ #3 1W/3R 33.3%."
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv-codex\Scripts\python.exe -m pytest tests\test_trackracerbot_helpers.py::test_leaderboard_response_formatting_limits_to_top_five tests\test_twitch_fixture_capture.py -k "leaderboard_and_stats or carstats_and_carleaderboard" -v
```

Expected: fail because current output uses `1.` and semicolon-separated entries.

- [ ] **Step 3: Implement shared rank marker helper**

Add to `trackracerbot.py` near response helpers:

```python
LEADERBOARD_RANK_MARKERS = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣")


def leaderboard_rank_marker(index: int) -> str:
    if 1 <= index <= len(LEADERBOARD_RANK_MARKERS):
        return LEADERBOARD_RANK_MARKERS[index - 1]
    return f"{index}."
```

Update both leaderboard builders to prefix each entry with `leaderboard_rank_marker(index)` and join entries with `" "`.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
.\.venv-codex\Scripts\python.exe -m pytest tests\test_trackracerbot_helpers.py::test_leaderboard_response_formatting_limits_to_top_five tests\test_twitch_fixture_capture.py -k "leaderboard_and_stats or carstats_and_carleaderboard" -v
```

Expected: pass.

- [ ] **Step 5: Run full verification**

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

Spec coverage: the plan updates both public leaderboard outputs, preserves empty states, and leaves rankings and database behavior unchanged.

Placeholder scan: no placeholders or deferred implementation requirements remain.

Type consistency: the shared helper is named `leaderboard_rank_marker(index: int) -> str` and is used by both leaderboard builders.
