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
def clear_entry_queue():
    trackracerbot.entry_queue.clear()
    trackracerbot.reset_submission_stats(None)
    trackracerbot.reset_response_rotation()
    trackracerbot.registration_open = True
    yield
    trackracerbot.entry_queue.clear()
    trackracerbot.reset_submission_stats(None)
    trackracerbot.reset_response_rotation()
    trackracerbot.registration_open = True


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
            "Available commands: !play // Mod Commands: !start !openentries !closeentries !clearentries"
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
            "Available commands: !play // Mod Commands: !start !openentries !closeentries !clearentries"
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

    assert outputs == ["Available commands: !play"]
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
        "Available commands: !play // Mod Commands: !start !openentries !closeentries !clearentries"
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
                "Available commands: !play // Mod Commands: !start !openentries !closeentries !clearentries"
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
    trackracerbot.entry_queue.clear()
    trackracerbot.entry_queue.extend(record.get("initial_entries", []))

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
            "Available commands: !play // Mod Commands: !start !openentries !closeentries !clearentries"
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
