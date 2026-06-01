import trackracerbot


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
