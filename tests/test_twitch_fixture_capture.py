import json

import pytest

import trackracerbot


class FakeAuthor:
    def __init__(self, is_mod):
        self.is_mod = is_mod


class FakeTwitchMessage:
    def __init__(self, is_mod):
        self.author = FakeAuthor(is_mod)


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
            "Available commands: !play !entries // Mod Commands: !start !clearentries"
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
            "Available commands: !play !entries // Mod Commands: !start !clearentries"
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

    assert outputs == ["Available commands: !play !entries"]
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
        "Available commands: !play !entries // Mod Commands: !start !clearentries"
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
                "Available commands: !play !entries // Mod Commands: !start !clearentries"
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
            "Available commands: !play !entries // Mod Commands: !start !clearentries"
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
        "bot_outputs": ["You have been added example_user"],
    }

    outputs = await replay_twitch_capture_record(record, monkeypatch, tmp_path)

    assert outputs == record["bot_outputs"]
    assert list(trackracerbot.entry_queue) == ["example_user"]
    assert (tmp_path / "entries.txt").exists()
