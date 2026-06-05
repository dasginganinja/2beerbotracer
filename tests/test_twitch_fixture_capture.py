import json
from pathlib import Path

import pytest

import trackracerbot


class FakeAuthor:
    def __init__(self, is_mod):
        self.is_mod = is_mod


class FakeTwitchMessage:
    def __init__(self, is_mod):
        self.author = FakeAuthor(is_mod)


@pytest.fixture(autouse=True)
def clear_entry_queue(tmp_path, monkeypatch):
    monkeypatch.setattr(
        trackracerbot,
        "entry_file_abs",
        str(tmp_path / "entries.txt"),
    )
    monkeypatch.setattr(
        trackracerbot,
        "bot_state_file_abs",
        str(tmp_path / "bot-state.json"),
    )
    monkeypatch.setattr(
        trackracerbot,
        "race_history_db_abs",
        str(tmp_path / "race-history.sqlite3"),
    )
    trackracerbot.entry_queue.clear()
    trackracerbot.reset_submission_stats(None)
    trackracerbot.submission_window["entries_opened_at_utc"] = None
    trackracerbot.submission_window["entries_closed_at_utc"] = None
    trackracerbot.reset_response_rotation()
    trackracerbot.registration_open = True
    yield
    trackracerbot.entry_queue.clear()
    trackracerbot.reset_submission_stats(None)
    trackracerbot.submission_window["entries_opened_at_utc"] = None
    trackracerbot.submission_window["entries_closed_at_utc"] = None
    trackracerbot.reset_response_rotation()
    trackracerbot.registration_open = True


def test_twitch_fixture_uses_temp_race_history_db_and_bot_state_by_default(tmp_path):
    assert str(tmp_path) in trackracerbot.race_history_db_abs
    assert str(tmp_path) in trackracerbot.bot_state_file_abs
    assert str(tmp_path) in trackracerbot.entry_file_abs


def test_chat_capture_is_disabled_when_file_path_is_empty(monkeypatch):
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")

    assert not trackracerbot.is_chat_capture_enabled()


def test_build_twitch_capture_record_contains_sanitized_fields():
    record = trackracerbot.build_twitch_capture_record(
        message="!commands",
        author="example_user",
        command=trackracerbot.COMMAND_COMMANDS,
        is_mod=True,
        bot_outputs=[
            "Available commands: !play !entries !winner !leaderboard !stats !carstats !carleaderboard !streamracestats // Mod Commands: !start !openentries !closeentries !clearentries !winner <number|name> !setlastwinner"
        ],
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    assert record == {
        "source": "twitch",
        "author": "example_user",
        "message": "!commands",
        "classification": "commands",
        "is_mod": True,
        "bot_outputs": [
            "Available commands: !play !entries !winner !leaderboard !stats !carstats !carleaderboard !streamracestats // Mod Commands: !start !openentries !closeentries !clearentries !winner <number|name> !setlastwinner"
        ],
    }


def test_write_chat_capture_record_appends_json_line(tmp_path, monkeypatch):
    capture_file = tmp_path / "captures" / "chat-fixtures.jsonl"
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", str(capture_file))

    trackracerbot.write_chat_capture_record(
        {
            "source": "twitch",
            "author": "example_user",
            "message": "!entries",
            "classification": "entries",
            "is_mod": False,
            "bot_outputs": ["Race Entries: example_user"],
        }
    )

    lines = capture_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {
        "source": "twitch",
        "author": "example_user",
        "message": "!entries",
        "classification": "entries",
        "is_mod": False,
        "bot_outputs": ["Race Entries: example_user"],
    }


@pytest.mark.asyncio
async def test_handle_message_capture_disabled_does_not_write_file(tmp_path, monkeypatch):
    capture_file = tmp_path / "chat-fixtures.jsonl"
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")

    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)

    await trackracerbot.handle_message(
        "!commands",
        "example_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == [
        "Available commands: !play !entries !winner !leaderboard !stats !carstats !carleaderboard !streamracestats"
    ]
    assert not capture_file.exists()


@pytest.mark.asyncio
async def test_handle_message_capture_enabled_writes_twitch_record(tmp_path, monkeypatch):
    capture_file = tmp_path / "chat-fixtures.jsonl"
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", str(capture_file))

    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)

    await trackracerbot.handle_message(
        "!commands",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    assert outputs == [
        "Available commands: !play !entries !winner !leaderboard !stats !carstats !carleaderboard !streamracestats // Mod Commands: !start !openentries !closeentries !clearentries !winner <number|name> !setlastwinner"
    ]
    records = [
        json.loads(line)
        for line in capture_file.read_text(encoding="utf-8").splitlines()
    ]
    assert records == [
        {
            "source": "twitch",
            "author": "example_mod",
            "message": "!commands",
            "classification": "commands",
            "is_mod": True,
            "bot_outputs": [
                "Available commands: !play !entries !winner !leaderboard !stats !carstats !carleaderboard !streamracestats // Mod Commands: !start !openentries !closeentries !clearentries !winner <number|name> !setlastwinner"
            ],
        }
    ]


async def replay_twitch_capture_record(record, monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(
        trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3")
    )
    trackracerbot.entry_queue.clear()
    trackracerbot.entry_queue.extend(record.get("initial_entries", []))
    if "initial_race_entries" in record:
        trackracerbot.race_history.start_race(
            trackracerbot.race_history_db_abs,
            record["initial_race_entries"],
        )
    if "initial_race_result" in record:
        trackracerbot.race_history.set_latest_race_result(
            trackracerbot.race_history_db_abs,
            record["initial_race_result"],
        )

    await trackracerbot.handle_message(
        record["message"],
        record["author"],
        twitch_message=FakeTwitchMessage(is_mod=record["is_mod"]),
    )

    return outputs


@pytest.mark.asyncio
async def test_replay_twitch_capture_record_verifies_command_output(monkeypatch, tmp_path):
    record = {
        "source": "twitch",
        "author": "example_mod",
        "message": "!commands",
        "classification": "commands",
        "is_mod": True,
        "bot_outputs": [
            "Available commands: !play !entries !winner !leaderboard !stats !carstats !carleaderboard !streamracestats // Mod Commands: !start !openentries !closeentries !clearentries !winner <number|name> !setlastwinner"
        ],
    }

    outputs = await replay_twitch_capture_record(record, monkeypatch, tmp_path)

    assert outputs == record["bot_outputs"]


@pytest.mark.asyncio
async def test_replay_twitch_capture_record_isolates_entry_file(monkeypatch, tmp_path):
    record = {
        "source": "twitch",
        "author": "example_user",
        "message": "!race",
        "classification": "entry",
        "is_mod": False,
        "bot_outputs": ["You're in, example_user. You're car #1."],
    }

    outputs = await replay_twitch_capture_record(record, monkeypatch, tmp_path)

    assert outputs == record["bot_outputs"]
    assert list(trackracerbot.entry_queue) == ["example_user"]
    assert (tmp_path / "entries.txt").exists()


@pytest.mark.asyncio
async def test_entry_response_includes_car_number_and_preserves_author_case(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))

    await trackracerbot.handle_message(
        "!race",
        "CAPSUser",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == ["You're in, CAPSUser. You're car #1."]
    assert list(trackracerbot.entry_queue) == ["CAPSUser"]


@pytest.mark.asyncio
async def test_accepted_entry_resets_signup_reminder_idle_timer(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot.time, "monotonic", lambda: 222.0)
    monkeypatch.setattr(trackracerbot, "last_signup_activity_at", 100.0)
    monkeypatch.setattr(trackracerbot, "signup_reminder_pending", False)

    await trackracerbot.handle_message(
        "!race",
        "new_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == ["You're in, new_user. You're car #1."]
    assert trackracerbot.last_signup_activity_at == 222.0
    assert trackracerbot.signup_reminder_pending


@pytest.mark.asyncio
async def test_twenty_ninth_entry_response_uses_display_car_number(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    trackracerbot.entry_queue.extend(f"racer_{index}" for index in range(28))

    await trackracerbot.handle_message(
        "!race",
        "NiceUser",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == ["Registered, NiceUser. You've got car #69."]


@pytest.mark.asyncio
async def test_entry_lookup_command_returns_name_for_display_number(monkeypatch):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    trackracerbot.entry_queue.extend(f"racer_{index}" for index in range(28))
    trackracerbot.entry_queue.append("NiceUser")

    await trackracerbot.handle_message(
        "!entry 69",
        "viewer",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == ["Car #69 is NiceUser."]


@pytest.mark.asyncio
async def test_entry_lookup_command_returns_display_number_for_name(monkeypatch):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    trackracerbot.entry_queue.extend(f"racer_{index}" for index in range(28))
    trackracerbot.entry_queue.append("NiceUser")

    await trackracerbot.handle_message(
        "!entry niceuser",
        "viewer",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == ["NiceUser is car #69."]


@pytest.mark.asyncio
async def test_entry_lookup_command_ignores_leading_at_for_name(monkeypatch):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    trackracerbot.entry_queue.extend(f"racer_{index}" for index in range(28))
    trackracerbot.entry_queue.append("NiceUser")

    await trackracerbot.handle_message(
        "!entry @niceuser",
        "viewer",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == ["NiceUser is car #69."]


@pytest.mark.asyncio
async def test_bare_entry_lookup_command_returns_callers_entry(monkeypatch):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    trackracerbot.entry_queue.extend(f"racer_{index}" for index in range(28))
    trackracerbot.entry_queue.append("NiceUser")

    await trackracerbot.handle_message(
        "!entry",
        "NiceUser",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == ["NiceUser is car #69."]


@pytest.mark.asyncio
async def test_bare_entry_lookup_command_reports_caller_not_entered(monkeypatch):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    trackracerbot.entry_queue.extend(["OtherUser"])

    await trackracerbot.handle_message(
        "!entry",
        "NiceUser",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == [
        "NiceUser, you're not in this race. Maybe the next one gets your moment."
    ]


@pytest.mark.asyncio
async def test_start_response_rotates_and_lowercases_lineup(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    trackracerbot.entry_queue.extend(["RacerONE", "RACERTwo"])

    await trackracerbot.handle_message(
        "!start",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    assert outputs == ["Starting grid locked: racerone, racertwo"]


@pytest.mark.asyncio
async def test_start_with_no_entries_is_blocked(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(
        trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3")
    )

    await trackracerbot.handle_message(
        "!start",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    assert outputs == ["No entries to start."]
    assert (
        trackracerbot.race_history.get_latest_race(trackracerbot.race_history_db_abs)
        is None
    )


@pytest.mark.asyncio
async def test_start_creates_pending_race_snapshot(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(
        trackracerbot, "bot_state_file_abs", str(tmp_path / "bot-state.json")
    )
    monkeypatch.setattr(
        trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3")
    )
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
async def test_start_persists_one_coherent_closed_registration_state(
    monkeypatch, tmp_path
):
    outputs = []
    snapshots = []
    opened_at = "2026-06-04T19:50:00+00:00"

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    original_write_registration_state = trackracerbot.write_registration_state

    def capturing_write_registration_state():
        original_write_registration_state()
        snapshots.append(
            json.loads(Path(trackracerbot.bot_state_file_abs).read_text(encoding="utf-8"))
        )

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(
        trackracerbot, "bot_state_file_abs", str(tmp_path / "bot-state.json")
    )
    monkeypatch.setattr(
        trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3")
    )
    monkeypatch.setattr(
        trackracerbot, "write_registration_state", capturing_write_registration_state
    )
    trackracerbot.entry_queue.extend(["RacerONE", "RACERTwo"])
    trackracerbot.registration_open = True
    trackracerbot.submission_window["entries_opened_at_utc"] = opened_at
    trackracerbot.submission_window["entries_closed_at_utc"] = None

    await trackracerbot.handle_message(
        "!start",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    state = json.loads(Path(trackracerbot.bot_state_file_abs).read_text(encoding="utf-8"))
    assert outputs == ["Starting grid locked: racerone, racertwo"]
    assert state["registration_open"] is False
    assert state["submission_window"]["entries_opened_at_utc"] == opened_at
    assert state["submission_window"]["entries_closed_at_utc"]
    assert all(
        not (
            snapshot["registration_open"]
            and snapshot["submission_window"]["entries_closed_at_utc"]
        )
        for snapshot in snapshots
    )


@pytest.mark.asyncio
async def test_start_same_lineup_replaces_pending_race(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(
        trackracerbot, "bot_state_file_abs", str(tmp_path / "bot-state.json")
    )
    monkeypatch.setattr(
        trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3")
    )
    trackracerbot.entry_queue.extend(["RacerONE", "RACERTwo"])

    await trackracerbot.handle_message(
        "!start", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True)
    )
    first_race = trackracerbot.race_history.get_latest_race(
        trackracerbot.race_history_db_abs
    )
    await trackracerbot.handle_message(
        "!start", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True)
    )
    second_race = trackracerbot.race_history.get_latest_race(
        trackracerbot.race_history_db_abs
    )

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
    monkeypatch.setattr(
        trackracerbot, "bot_state_file_abs", str(tmp_path / "bot-state.json")
    )
    monkeypatch.setattr(
        trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3")
    )
    trackracerbot.entry_queue.extend(["RacerONE"])

    await trackracerbot.handle_message(
        "!start", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True)
    )
    trackracerbot.entry_queue.clear()
    trackracerbot.entry_queue.extend(["DifferentRacer"])
    await trackracerbot.handle_message(
        "!start", "example_mod", twitch_message=FakeTwitchMessage(is_mod=True)
    )

    assert outputs[-1] == (
        "Record the last winner first: !winner {number or name}. "
        "Use !setlastwinner skipped if there was no winner."
    )


@pytest.mark.asyncio
async def test_start_locks_registration_and_blocks_new_entries(monkeypatch, tmp_path):
    outputs = []
    state_file = tmp_path / "bot-state.json"

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    trackracerbot.entry_queue.extend(["RacerONE", "RACERTwo"])

    await trackracerbot.handle_message(
        "!start",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )
    await trackracerbot.handle_message(
        "!race",
        "late_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == [
        "Starting grid locked: racerone, racertwo",
        "Grid is locked, late_user.",
    ]
    assert list(trackracerbot.entry_queue) == ["RacerONE", "RACERTwo"]
    trackracerbot.registration_open = True
    trackracerbot.load_registration_state()
    assert not trackracerbot.registration_open


@pytest.mark.asyncio
async def test_clear_entries_reopens_registration(monkeypatch, tmp_path):
    outputs = []
    state_file = tmp_path / "bot-state.json"

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    monkeypatch.setattr(trackracerbot.time, "monotonic", lambda: 333.0)
    monkeypatch.setattr(trackracerbot, "last_signup_activity_at", 100.0)
    monkeypatch.setattr(trackracerbot, "signup_reminder_pending", False)
    trackracerbot.registration_open = False
    trackracerbot.entry_queue.extend(["racer_one", "racer_two"])

    await trackracerbot.handle_message(
        "!clearentries",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )
    await trackracerbot.handle_message(
        "!race",
        "new_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == [
        "All entries have been cleared.",
        "You're in, new_user. You're car #1.",
    ]
    assert list(trackracerbot.entry_queue) == ["new_user"]
    trackracerbot.registration_open = False
    trackracerbot.load_registration_state()
    assert trackracerbot.registration_open
    assert trackracerbot.last_signup_activity_at == 333.0
    assert trackracerbot.signup_reminder_pending


@pytest.mark.asyncio
async def test_open_entries_reopens_registration_without_clearing_queue(monkeypatch, tmp_path):
    outputs = []
    state_file = tmp_path / "bot-state.json"

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    monkeypatch.setattr(trackracerbot.time, "monotonic", lambda: 444.0)
    monkeypatch.setattr(trackracerbot, "last_signup_activity_at", 100.0)
    monkeypatch.setattr(trackracerbot, "signup_reminder_pending", False)
    trackracerbot.registration_open = False
    trackracerbot.entry_queue.extend(["racer_one", "racer_two"])

    await trackracerbot.handle_message(
        "!openentries",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )
    await trackracerbot.handle_message(
        "!race",
        "new_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == [
        "Entries are open.",
        "Added to the grid, new_user. You're car #3.",
    ]
    assert list(trackracerbot.entry_queue) == ["racer_one", "racer_two", "new_user"]
    trackracerbot.registration_open = False
    trackracerbot.load_registration_state()
    assert trackracerbot.registration_open
    assert trackracerbot.last_signup_activity_at == 444.0
    assert trackracerbot.signup_reminder_pending


@pytest.mark.asyncio
async def test_non_mod_open_entries_does_not_reopen_registration(monkeypatch, tmp_path):
    outputs = []
    state_file = tmp_path / "bot-state.json"

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    trackracerbot.registration_open = False
    trackracerbot.set_registration_open(False)

    await trackracerbot.handle_message(
        "!openentries",
        "example_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == []
    assert not trackracerbot.registration_open


@pytest.mark.asyncio
async def test_close_entries_closes_registration_without_clearing_queue(monkeypatch, tmp_path):
    outputs = []
    state_file = tmp_path / "bot-state.json"

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    trackracerbot.registration_open = True
    trackracerbot.entry_queue.extend(["racer_one", "racer_two"])

    await trackracerbot.handle_message(
        "!closeentries",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    assert outputs == ["entries closed"]
    assert list(trackracerbot.entry_queue) == ["racer_one", "racer_two"]
    assert not trackracerbot.registration_open
    trackracerbot.registration_open = True
    trackracerbot.load_registration_state()
    assert not trackracerbot.registration_open


@pytest.mark.asyncio
async def test_non_mod_close_entries_does_not_close_registration(monkeypatch, tmp_path):
    outputs = []
    state_file = tmp_path / "bot-state.json"

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    trackracerbot.registration_open = True
    trackracerbot.set_registration_open(True)

    await trackracerbot.handle_message(
        "!closeentries",
        "example_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == []
    assert trackracerbot.registration_open


@pytest.mark.asyncio
async def test_duplicate_entry_response_rotates_and_includes_car_number(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    trackracerbot.entry_queue.extend(["first_user", "CAPSUser"])

    await trackracerbot.handle_message(
        "!race",
        "CAPSUser",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )
    await trackracerbot.handle_message(
        "!race",
        "CAPSUser",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    assert outputs == [
        "You're already in, CAPSUser. You're car #2.",
        "You're on the grid already, CAPSUser. Car #2 is yours.",
    ]


def load_jsonl_fixture(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.asyncio
async def test_replay_twitch_command_fixture_covers_all_commands(monkeypatch, tmp_path):
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "twitch"
        / "all_commands.jsonl"
    )
    records = load_jsonl_fixture(fixture_path)

    assert [record["case"] for record in records] == [
        "commands_non_mod",
        "commands_mod",
        "entries",
        "race",
        "play",
        "enter",
        "join",
        "race_duplicate",
        "play_duplicate",
        "enter_duplicate",
        "join_duplicate",
        "emote_duplicate",
        "start_mod",
        "openentries_mod",
        "closeentries_mod",
        "clearentries_mod",
        "winner_read",
        "leaderboard",
        "stats_self",
        "carstats_usage",
        "carleaderboard_empty",
        "streamracestats_empty",
        "set_last_winner",
    ]

    for index, record in enumerate(records):
        record_tmp_path = tmp_path / str(index)
        record_tmp_path.mkdir()

        outputs = await replay_twitch_capture_record(
            record,
            monkeypatch,
            record_tmp_path,
        )

        assert outputs == record["bot_outputs"]


@pytest.mark.asyncio
async def test_clear_entries_starts_submission_stats_timer(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot.time, "monotonic", lambda: 100.0)
    trackracerbot.entry_queue.extend(["racer_one", "racer_two"])

    await trackracerbot.handle_message(
        "!clearentries",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    assert outputs == ["All entries have been cleared."]
    assert trackracerbot.submission_stats["started_at"] == 100.0
    assert trackracerbot.submission_stats["accepted_entries"] == 0
    assert trackracerbot.submission_stats["twitch_entries"] == 0
    assert not trackracerbot.submission_stats["reported"]


@pytest.mark.asyncio
async def test_full_entry_list_reports_elapsed_time_and_twitch_percentage(monkeypatch, tmp_path):
    outputs = []
    current_time = 200.0

    def fake_monotonic():
        return current_time

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot.time, "monotonic", fake_monotonic)

    await trackracerbot.handle_message(
        "!clearentries",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    current_time = 327.0
    for index in range(21):
        await trackracerbot.handle_message(
            "!race",
            f"twitch_user_{index}",
            twitch_message=FakeTwitchMessage(is_mod=False),
        )

    for index in range(9):
        await trackracerbot.handle_message(
            "!race",
            f"youtube_user_{index}",
            youtube_message={"authorDetails": {"isChatOwner": False, "isChatModerator": False}},
        )

    assert outputs[-1] == (
        "Entry list filled in 2m 7s. Twitch entries: 70.0% (21/30)."
    )
    assert trackracerbot.submission_stats["reported"]


@pytest.mark.asyncio
async def test_submission_stats_survive_restart_mid_signups(monkeypatch, tmp_path):
    outputs = []
    current_time = 100.0
    state_file = tmp_path / "bot-state.json"

    def fake_monotonic():
        return current_time

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    monkeypatch.setattr(trackracerbot.time, "monotonic", fake_monotonic)

    await trackracerbot.handle_message(
        "!clearentries",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )

    current_time = 130.0
    for index in range(10):
        await trackracerbot.handle_message(
            "!race",
            f"twitch_user_{index}",
            twitch_message=FakeTwitchMessage(is_mod=False),
        )

    restored_entries = list(trackracerbot.entry_queue)
    trackracerbot.reset_submission_stats(None, persist=False)
    trackracerbot.entry_queue.clear()
    trackracerbot.entry_queue.extend(restored_entries)
    trackracerbot.load_registration_state()

    current_time = 280.0
    for index in range(20):
        await trackracerbot.handle_message(
            "!race",
            f"youtube_user_{index}",
            youtube_message={"authorDetails": {"isChatOwner": False, "isChatModerator": False}},
        )

    assert outputs[-1] == (
        "Entry list filled in 3m 0s. Twitch entries: 33.3% (10/30)."
    )


@pytest.mark.asyncio
async def test_submission_stats_do_not_count_duplicates_or_report_twice(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "entry_file_abs", str(tmp_path / "entries.txt"))
    monkeypatch.setattr(trackracerbot.time, "monotonic", lambda: 10.0)

    await trackracerbot.handle_message(
        "!clearentries",
        "example_mod",
        twitch_message=FakeTwitchMessage(is_mod=True),
    )
    await trackracerbot.handle_message(
        "!race",
        "duplicate_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )
    await trackracerbot.handle_message(
        "!race",
        "duplicate_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    for index in range(29):
        await trackracerbot.handle_message(
            "!race",
            f"youtube_user_{index}",
            youtube_message={"authorDetails": {"isChatOwner": False, "isChatModerator": False}},
        )

    await trackracerbot.handle_message(
        "!race",
        "late_user",
        twitch_message=FakeTwitchMessage(is_mod=False),
    )

    stats_outputs = [
        output
        for output in outputs
        if output.startswith("Entry list filled in ")
    ]
    assert stats_outputs == [
        "Entry list filled in 0s. Twitch entries: 3.3% (1/30)."
    ]


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
        "Top winners: 1️⃣ RacerTwo 2W/3R 66.7% 2️⃣ RacerOne 1W/3R 33.3%.",
        "RacerTwo: 2W / 3R / 66.7%.",
        "RacerOne: 1W / 3R / 33.3%.",
    ]


@pytest.mark.asyncio
async def test_carstats_and_carleaderboard_commands_report_car_history(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    db_path = str(tmp_path / "race-history.sqlite3")
    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", db_path)
    trackracerbot.race_history.start_race(db_path, ["Alice", "Bob", "Cara"])
    trackracerbot.race_history.complete_latest_pending_race(db_path, "Bob")
    trackracerbot.race_history.start_race(db_path, ["Dana", "Eli", "Fay"])
    trackracerbot.race_history.complete_latest_pending_race(db_path, "Eli")
    trackracerbot.race_history.start_race(db_path, ["Gus", "Hal", "Ivy"])
    trackracerbot.race_history.complete_latest_pending_race(db_path, "Ivy")

    await trackracerbot.handle_message("!carstats 2", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))
    await trackracerbot.handle_message("!carleaderboard", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))

    assert outputs == [
        "Car #2: 2W / 3R / 66.7%. Best driver: Bob 1W. Last win: Eli.",
        "Top cars: 1️⃣ #2 2W/3R 66.7% 2️⃣ #3 1W/3R 33.3%.",
    ]


@pytest.mark.asyncio
async def test_carstats_command_reports_usage_and_missing_car(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    db_path = str(tmp_path / "race-history.sqlite3")
    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", db_path)
    trackracerbot.race_history.start_race(db_path, ["Alice"])

    await trackracerbot.handle_message("!carstats", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))
    await trackracerbot.handle_message("!carstats nope", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))
    await trackracerbot.handle_message("!carstats 7", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))

    assert outputs == [
        "Usage: !carstats <number>",
        "Usage: !carstats <number>",
        "No races recorded for car #7.",
    ]


@pytest.mark.asyncio
async def test_carleaderboard_command_reports_empty_state(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))

    await trackracerbot.handle_message("!carleaderboard", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))

    assert outputs == ["No completed car winners yet."]


@pytest.mark.asyncio
async def test_streamracestats_command_reports_stream_summary(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    db_path = str(tmp_path / "race-history.sqlite3")
    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", db_path)
    monkeypatch.setattr(
        trackracerbot,
        "stream_race_stats_cutoff",
        lambda: "2026-06-05T16:00:00+00:00",
        raising=False,
    )
    trackracerbot.race_history.start_race(
        db_path, ["OldWinner"], started_at_utc="2026-06-05T15:59:00+00:00"
    )
    trackracerbot.race_history.complete_latest_pending_race(db_path, "OldWinner")
    trackracerbot.race_history.start_race(
        db_path, ["Alice", "Bob"], started_at_utc="2026-06-05T16:00:00+00:00"
    )
    trackracerbot.race_history.complete_latest_pending_race(db_path, "Alice")
    trackracerbot.race_history.start_race(
        db_path, ["Cara", "Dan"], started_at_utc="2026-06-05T16:15:00+00:00"
    )
    trackracerbot.race_history.complete_latest_pending_race(db_path, "Dan")
    trackracerbot.race_history.start_race(
        db_path, ["Alice", "Eli"], started_at_utc="2026-06-05T16:30:00+00:00"
    )
    trackracerbot.race_history.complete_latest_pending_race(db_path, "Alice")
    trackracerbot.race_history.start_race(
        db_path, ["Pending"], started_at_utc="2026-06-05T16:45:00+00:00"
    )
    trackracerbot.race_history.start_race(
        db_path, ["Skipped"], started_at_utc="2026-06-05T17:00:00+00:00"
    )
    trackracerbot.race_history.set_latest_race_result(db_path, "skipped")

    await trackracerbot.handle_message("!streamracestats", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))

    assert outputs == [
        "Stream Race Stats 🏁 Races: 5 total / 3 completed / 1 pending / 1 skipped 🏆 Winners: 1️⃣ Alice #1 2️⃣ Dan #2 3️⃣ Alice #1",
        "Stream Leaders 🏆 Drivers: Alice 2W / Dan 1W 🚗 Cars: #1 2W / #2 1W 🎯 Unique winners: 2",
    ]


@pytest.mark.asyncio
async def test_streamracestats_command_reports_empty_summary(monkeypatch, tmp_path):
    outputs = []

    async def fake_print_everywhere(logmessage, twitch_message=None):
        outputs.append(logmessage)

    monkeypatch.setattr(trackracerbot, "print_everywhere", fake_print_everywhere)
    monkeypatch.setattr(trackracerbot, "CHAT_CAPTURE_FILE", "")
    monkeypatch.setattr(trackracerbot, "race_history_db_abs", str(tmp_path / "race-history.sqlite3"))
    monkeypatch.setattr(
        trackracerbot,
        "stream_race_stats_cutoff",
        lambda: "2026-06-05T16:00:00+00:00",
        raising=False,
    )

    await trackracerbot.handle_message("!streamracestats", "viewer", twitch_message=FakeTwitchMessage(is_mod=False))

    assert outputs == [
        "Stream Race Stats 🏁 Races: 0 total / 0 completed / 0 pending / 0 skipped 🏆 Winners: none"
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
