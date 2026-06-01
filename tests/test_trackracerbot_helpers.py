import trackracerbot


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
    assert trackracerbot.is_clear_entries_message("!clearentries")
    assert trackracerbot.is_clear_entries_message("!CLEARENTRIES now")
    assert trackracerbot.is_entries_message("!entries")
    assert trackracerbot.is_entries_message("!ENTRIES please")


def test_command_detection_helpers_reject_non_matching_messages():
    assert not trackracerbot.is_commands_message("commands")
    assert not trackracerbot.is_commands_message("hello !commands")
    assert not trackracerbot.is_start_message("start")
    assert not trackracerbot.is_start_message("hello !start")
    assert not trackracerbot.is_clear_entries_message("clearentries")
    assert not trackracerbot.is_clear_entries_message("hello !clearentries")
    assert not trackracerbot.is_entries_message("entries")
    assert not trackracerbot.is_entries_message("hello !entries")


def test_classify_message_returns_expected_command_labels():
    assert trackracerbot.classify_message("!commands") == trackracerbot.COMMAND_COMMANDS
    assert trackracerbot.classify_message("!race") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("artmannJudy") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("!start") == trackracerbot.COMMAND_START
    assert trackracerbot.classify_message("!clearentries") == trackracerbot.COMMAND_CLEAR_ENTRIES
    assert trackracerbot.classify_message("!entries") == trackracerbot.COMMAND_ENTRIES
    assert trackracerbot.classify_message("just chatting") == trackracerbot.COMMAND_UNKNOWN


def test_classify_message_preserves_case_and_prefix_behavior():
    assert trackracerbot.classify_message("!COMMANDS") == trackracerbot.COMMAND_COMMANDS
    assert trackracerbot.classify_message("!PLAY please") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("x100pr3Hndoclap52 extra words") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("hello artmannJudy") == trackracerbot.COMMAND_UNKNOWN


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
