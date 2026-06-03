import trackracerbot
import pytest


class FakeAuthor:
    def __init__(self, is_mod):
        self.is_mod = is_mod


class FakeTwitchMessage:
    def __init__(self, author):
        self.author = author


def test_is_entry_message_accepts_existing_text_commands_case_insensitively():
    assert trackracerbot.is_entry_message("!race")
    assert trackracerbot.is_entry_message("!PLAY")
    assert trackracerbot.is_entry_message("!Enter me please")
    assert trackracerbot.is_entry_message("!join")


def test_is_entry_message_accepts_existing_emote_prefixes():
    assert trackracerbot.is_entry_message("artmannJudy")
    assert trackracerbot.is_entry_message("x100pr3Hndoclap52 extra words")
    assert trackracerbot.is_entry_message("x2beerShrek")
    assert trackracerbot.is_entry_message("avoidr3Hotdogman")
    assert trackracerbot.is_entry_message("spacec122GoodVibes")
    assert trackracerbot.is_entry_message("artmannNatmar")
    assert trackracerbot.is_entry_message("artmannOhyeah")


def test_is_entry_message_keeps_current_prefix_only_emote_behavior():
    assert not trackracerbot.is_entry_message("hello artmannJudy")
    assert not trackracerbot.is_entry_message("hello x2beerShrek")


def test_is_entry_message_rejects_non_entry_messages():
    assert not trackracerbot.is_entry_message("!entries")
    assert not trackracerbot.is_entry_message("!commands")
    assert not trackracerbot.is_entry_message("just chatting")


def test_command_detection_helpers_accept_current_prefixes_case_insensitively():
    assert trackracerbot.is_commands_message("!commands")
    assert trackracerbot.is_commands_message("!COMMANDS please")
    assert trackracerbot.is_start_message("!start")
    assert trackracerbot.is_start_message("!START race")
    assert trackracerbot.is_open_entries_message("!openentries")
    assert trackracerbot.is_open_entries_message("!OPENENTRIES now")
    assert trackracerbot.is_close_entries_message("!closeentries")
    assert trackracerbot.is_close_entries_message("!CLOSEENTRIES now")
    assert trackracerbot.is_clear_entries_message("!clearentries")
    assert trackracerbot.is_clear_entries_message("!CLEARENTRIES now")
    assert trackracerbot.is_entries_message("!entries")
    assert trackracerbot.is_entries_message("!ENTRIES please")


def test_command_detection_helpers_reject_non_matching_messages():
    assert not trackracerbot.is_commands_message("commands")
    assert not trackracerbot.is_commands_message("hello !commands")
    assert not trackracerbot.is_start_message("start")
    assert not trackracerbot.is_start_message("hello !start")
    assert not trackracerbot.is_open_entries_message("openentries")
    assert not trackracerbot.is_open_entries_message("hello !openentries")
    assert not trackracerbot.is_close_entries_message("closeentries")
    assert not trackracerbot.is_close_entries_message("hello !closeentries")
    assert not trackracerbot.is_clear_entries_message("clearentries")
    assert not trackracerbot.is_clear_entries_message("hello !clearentries")
    assert not trackracerbot.is_entries_message("entries")
    assert not trackracerbot.is_entries_message("hello !entries")


def test_classify_message_returns_expected_command_labels():
    assert trackracerbot.classify_message("!commands") == trackracerbot.COMMAND_COMMANDS
    assert trackracerbot.classify_message("!race") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("artmannJudy") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("!start") == trackracerbot.COMMAND_START
    assert trackracerbot.classify_message("!openentries") == trackracerbot.COMMAND_OPEN_ENTRIES
    assert trackracerbot.classify_message("!closeentries") == trackracerbot.COMMAND_CLOSE_ENTRIES
    assert trackracerbot.classify_message("!clearentries") == trackracerbot.COMMAND_CLEAR_ENTRIES
    assert trackracerbot.classify_message("!entries") == trackracerbot.COMMAND_ENTRIES
    assert trackracerbot.classify_message("just chatting") == trackracerbot.COMMAND_UNKNOWN


def test_classify_message_preserves_case_and_prefix_behavior():
    assert trackracerbot.classify_message("!COMMANDS") == trackracerbot.COMMAND_COMMANDS
    assert trackracerbot.classify_message("!PLAY please") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("x100pr3Hndoclap52 extra words") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("hello artmannJudy") == trackracerbot.COMMAND_UNKNOWN


def test_build_entry_response_rotates_and_preserves_author_case():
    assert trackracerbot.build_entry_response("CAPSUser", 1) == (
        "You're in, CAPSUser. You're car #1."
    )
    assert trackracerbot.build_entry_response("AnotherUSER", 2) == (
        "Locked in, AnotherUSER. You're car #2."
    )


def test_build_entry_response_wraps_template_cycle():
    template_count = len(trackracerbot.ENTRY_RESPONSE_TEMPLATES)

    assert trackracerbot.build_entry_response("CycleUSER", template_count + 1) == (
        "You're in, CycleUSER. You're car #9."
    )


def test_build_duplicate_entry_response_rotates_and_preserves_author_case():
    assert trackracerbot.build_duplicate_entry_response("CAPSUser", 3, 0) == (
        "You're already in, CAPSUser. You're car #3."
    )
    assert trackracerbot.build_duplicate_entry_response("CAPSUser", 3, 1) == (
        "You're on the grid already, CAPSUser. Car #3 is yours."
    )


def test_build_start_response_rotates_and_lowercases_lineup_names():
    assert trackracerbot.build_start_response(["RacerONE", "RACERTwo"], 0) == (
        "Starting grid locked: racerone, racertwo"
    )
    assert trackracerbot.build_start_response(["RacerONE", "RACERTwo"], 1) == (
        "Rolling out with: racerone, racertwo"
    )


def test_build_registration_closed_response_points_to_entries_check():
    assert trackracerbot.build_registration_closed_response("CAPSUser") == (
        "Grid is locked, CAPSUser. Use !entries to check the lineup."
    )


def test_build_welcome_message_replaces_bot_name_and_rotates():
    assert trackracerbot.build_welcome_message("RaceBot", 0) == (
        "RaceBot is here. The treadmill is moving, the cars are confused, and entries are open."
    )
    assert trackracerbot.build_welcome_message("RaceBot", 1) == (
        "RaceBot has arrived at race control. Please submit your tiny machines and oversized confidence."
    )


def test_build_welcome_message_wraps_template_cycle():
    template_count = len(trackracerbot.WELCOME_MESSAGE_TEMPLATES)

    assert trackracerbot.build_welcome_message("RaceBot", template_count) == (
        "RaceBot is here. The treadmill is moving, the cars are confused, and entries are open."
    )


def test_build_costreaming_status_message_reports_registration_state():
    assert trackracerbot.build_costreaming_status_message(True) == (
        "Costreaming mode enabled. Reading the chat. Races are open currently."
    )
    assert trackracerbot.build_costreaming_status_message(False) == (
        "Costreaming mode enabled. Reading the chat. Races are closed currently."
    )


@pytest.mark.asyncio
async def test_send_welcome_message_queues_twitch_chat_message(monkeypatch):
    queue = trackracerbot.asyncio.Queue()
    monkeypatch.setattr(trackracerbot, "twitch_message_queue", queue)
    monkeypatch.setattr(trackracerbot, "twitch_channel_ref", object())
    monkeypatch.setattr(trackracerbot, "BOT_NAME", "RaceBot")
    monkeypatch.setattr(trackracerbot, "registration_open", True)

    await trackracerbot.send_welcome_message()

    assert await queue.get() == (
        "RaceBot is here. The treadmill is moving, the cars are confused, and entries are open."
    )
    assert queue.get_nowait() == (
        "Costreaming mode enabled. Reading the chat. Races are open currently."
    )


def test_missing_registration_state_infers_open_when_queue_is_empty(tmp_path, monkeypatch):
    state_file = tmp_path / "bot-state.json"
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    trackracerbot.entry_queue.clear()

    trackracerbot.load_registration_state()

    assert trackracerbot.registration_open


def test_missing_registration_state_infers_closed_when_queue_has_restored_entries(tmp_path, monkeypatch):
    state_file = tmp_path / "bot-state.json"
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    trackracerbot.entry_queue.clear()
    trackracerbot.entry_queue.extend(["racer_one"])

    trackracerbot.load_registration_state()

    assert not trackracerbot.registration_open


def test_registration_state_round_trips_to_json(tmp_path, monkeypatch):
    state_file = tmp_path / "bot-state.json"
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))

    trackracerbot.set_registration_open(False)
    trackracerbot.registration_open = True
    trackracerbot.load_registration_state()

    assert not trackracerbot.registration_open


def test_is_moderator_message_source_detects_twitch_mods():
    assert trackracerbot.is_moderator_message_source(
        twitch_message=FakeTwitchMessage(FakeAuthor(True))
    )
    assert not trackracerbot.is_moderator_message_source(
        twitch_message=FakeTwitchMessage(FakeAuthor(False))
    )


def test_is_moderator_message_source_handles_missing_twitch_author():
    assert not trackracerbot.is_moderator_message_source(
        twitch_message=FakeTwitchMessage(None)
    )


def test_is_moderator_message_source_preserves_youtube_owner_and_moderator_flags():
    assert trackracerbot.is_moderator_message_source(
        youtube_message={"authorDetails": {"isChatOwner": True, "isChatModerator": False}}
    )
    assert trackracerbot.is_moderator_message_source(
        youtube_message={"authorDetails": {"isChatOwner": False, "isChatModerator": True}}
    )
    assert not trackracerbot.is_moderator_message_source(
        youtube_message={"authorDetails": {"isChatOwner": False, "isChatModerator": False}}
    )
