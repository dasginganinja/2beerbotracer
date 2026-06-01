import json

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
