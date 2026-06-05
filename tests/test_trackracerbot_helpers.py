from datetime import datetime, timedelta, timezone

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
    assert trackracerbot.is_entry_message("x2beerRace")
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
    assert trackracerbot.is_entry_lookup_message("!entry 12")
    assert trackracerbot.is_entry_lookup_message("!ENTRY racer")


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
    assert not trackracerbot.is_entry_lookup_message("entry 12")
    assert not trackracerbot.is_entry_lookup_message("hello !entry 12")


def test_classify_message_returns_expected_command_labels():
    assert trackracerbot.classify_message("!commands") == trackracerbot.COMMAND_COMMANDS
    assert trackracerbot.classify_message("!race") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("artmannJudy") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("!start") == trackracerbot.COMMAND_START
    assert trackracerbot.classify_message("!openentries") == trackracerbot.COMMAND_OPEN_ENTRIES
    assert trackracerbot.classify_message("!closeentries") == trackracerbot.COMMAND_CLOSE_ENTRIES
    assert trackracerbot.classify_message("!clearentries") == trackracerbot.COMMAND_CLEAR_ENTRIES
    assert trackracerbot.classify_message("!entries") == trackracerbot.COMMAND_ENTRIES
    assert trackracerbot.classify_message("!entry 12") == trackracerbot.COMMAND_ENTRY_LOOKUP
    assert trackracerbot.classify_message("just chatting") == trackracerbot.COMMAND_UNKNOWN


def test_classify_message_preserves_case_and_prefix_behavior():
    assert trackracerbot.classify_message("!COMMANDS") == trackracerbot.COMMAND_COMMANDS
    assert trackracerbot.classify_message("!PLAY please") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("x100pr3Hndoclap52 extra words") == trackracerbot.COMMAND_ENTRY
    assert trackracerbot.classify_message("hello artmannJudy") == trackracerbot.COMMAND_UNKNOWN


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
        "Top winners: 1️⃣ racer_1 5W/10R 50.0% "
        "2️⃣ racer_2 4W/10R 50.0% "
        "3️⃣ racer_3 3W/10R 50.0% "
        "4️⃣ racer_4 2W/10R 50.0% "
        "5️⃣ racer_5 1W/10R 50.0%."
    )


def test_stream_race_stats_cutoff_uses_today_noon_after_noon():
    eastern_daylight = timezone(timedelta(hours=-4))

    assert trackracerbot.stream_race_stats_cutoff(
        datetime(2026, 6, 5, 17, 0, tzinfo=timezone.utc),
        eastern_daylight,
    ) == datetime(2026, 6, 5, 16, 0, tzinfo=timezone.utc)


def test_stream_race_stats_cutoff_uses_previous_noon_before_noon():
    eastern_daylight = timezone(timedelta(hours=-4))

    assert trackracerbot.stream_race_stats_cutoff(
        datetime(2026, 6, 5, 14, 0, tzinfo=timezone.utc),
        eastern_daylight,
    ) == datetime(2026, 6, 4, 16, 0, tzinfo=timezone.utc)


def test_build_stream_race_stats_messages_uses_one_or_two_messages():
    populated_summary = {
        "total": 5,
        "completed": 3,
        "pending": 1,
        "skipped": 1,
        "winners": [
            {"name": "Alice", "display_number": 1},
            {"name": "Dan", "display_number": 2},
            {"name": "Alice", "display_number": 1},
        ],
        "top_drivers": [
            {"name": "Alice", "wins": 2},
            {"name": "Dan", "wins": 1},
        ],
        "top_cars": [
            {"display_number": 1, "wins": 2},
            {"display_number": 2, "wins": 1},
        ],
        "unique_winners": 2,
    }
    empty_summary = {
        "total": 0,
        "completed": 0,
        "pending": 0,
        "skipped": 0,
        "winners": [],
        "top_drivers": [],
        "top_cars": [],
        "unique_winners": 0,
    }

    assert trackracerbot.build_stream_race_stats_messages(populated_summary) == [
        "Stream Race Stats 🏁 Races: 5 total / 3 completed / 1 pending / 1 skipped 🏆 Winners: 1️⃣ Alice #1 2️⃣ Dan #2 3️⃣ Alice #1",
        "Stream Leaders 🏆 Drivers: Alice 2W / Dan 1W 🚗 Cars: #1 2W / #2 1W 🎯 Unique winners: 2",
    ]
    assert trackracerbot.build_stream_race_stats_messages(empty_summary) == [
        "Stream Race Stats 🏁 Races: 0 total / 0 completed / 0 pending / 0 skipped 🏆 Winners: none"
    ]


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


def test_display_car_number_maps_position_29_to_69():
    assert trackracerbot.display_car_number(1) == 1
    assert trackracerbot.display_car_number(28) == 28
    assert trackracerbot.display_car_number(29) == 69
    assert trackracerbot.display_car_number(30) == 30


def test_build_entry_response_uses_display_car_number():
    assert trackracerbot.build_entry_response("NiceUser", 29) == (
        "Registered, NiceUser. You've got car #69."
    )


def test_build_duplicate_entry_response_rotates_and_preserves_author_case():
    assert trackracerbot.build_duplicate_entry_response("CAPSUser", 3, 0) == (
        "You're already in, CAPSUser. You're car #3."
    )
    assert trackracerbot.build_duplicate_entry_response("CAPSUser", 3, 1) == (
        "You're on the grid already, CAPSUser. Car #3 is yours."
    )


def test_build_duplicate_entry_response_uses_display_car_number():
    assert trackracerbot.build_duplicate_entry_response("NiceUser", 29, 0) == (
        "You're already in, NiceUser. You're car #69."
    )


def test_find_entry_by_display_number_uses_display_car_numbers():
    queue = ["car_one", "car_two"] + [f"racer_{index}" for index in range(3, 30)]

    assert trackracerbot.find_entry_by_display_number(queue, 1) == ("car_one", 1)
    assert trackracerbot.find_entry_by_display_number(queue, 69) == ("racer_29", 29)
    assert trackracerbot.find_entry_by_display_number(queue, 29) is None


def test_find_entry_by_name_matches_case_insensitively():
    queue = ["RacerOne", "CAPSUser"]

    assert trackracerbot.find_entry_by_name(queue, "capsuser") == ("CAPSUser", 2)
    assert trackracerbot.find_entry_by_name(queue, "@capsuser") == ("CAPSUser", 2)
    assert trackracerbot.find_entry_by_name(queue, " missing ") is None


def test_build_entry_lookup_response_by_number_and_name():
    assert trackracerbot.build_entry_lookup_response("69", ["racer"] * 28 + ["NiceUser"]) == (
        "Car #69 is NiceUser."
    )
    assert trackracerbot.build_entry_lookup_response("niceuser", ["racer"] * 28 + ["NiceUser"]) == (
        "NiceUser is car #69."
    )
    assert trackracerbot.build_entry_lookup_response("@niceuser", ["racer"] * 28 + ["NiceUser"]) == (
        "NiceUser is car #69."
    )
    assert trackracerbot.build_entry_lookup_response("wat", ["NiceUser"]) == (
        "No entry found for wat."
    )


def test_build_own_entry_lookup_response_reports_caller_entry():
    assert trackracerbot.build_own_entry_lookup_response("NiceUser", ["racer"] * 28 + ["NiceUser"]) == (
        "NiceUser is car #69."
    )


def test_build_own_entry_lookup_response_reports_caller_not_entered():
    assert trackracerbot.build_own_entry_lookup_response("NiceUser", ["OtherUser"]) == (
        "NiceUser, you're not in this race. Maybe the next one gets your moment."
    )


def test_build_start_response_rotates_and_lowercases_lineup_names():
    assert trackracerbot.build_start_response(["RacerONE", "RACERTwo"], 0) == (
        "Starting grid locked: racerone, racertwo"
    )
    assert trackracerbot.build_start_response(["RacerONE", "RACERTwo"], 1) == (
        "Rolling out with: racerone, racertwo"
    )


def test_build_registration_closed_response_does_not_advertise_entries_command():
    assert trackracerbot.build_registration_closed_response("CAPSUser") == (
        "Grid is locked, CAPSUser."
    )


def test_build_welcome_message_replaces_bot_name_and_rotates():
    assert trackracerbot.build_welcome_message("RaceBot", 0, True) == (
        "RaceBot is here. The treadmill is moving, the cars are confused, and entries are open."
    )
    assert trackracerbot.build_welcome_message("RaceBot", 1, True) == (
        "RaceBot has arrived at race control. Please submit your tiny machines and oversized confidence."
    )


def test_build_welcome_message_respects_closed_registration_state():
    assert trackracerbot.build_welcome_message("RaceBot", 0, False) == (
        "RaceBot is here. The treadmill is moving, the cars are confused, and entries are closed."
    )
    assert trackracerbot.build_welcome_message("RaceBot", 6, False) == (
        "RaceBot is live. Entries are closed for whatever this beautiful motorsport mistake is."
    )
    assert trackracerbot.build_welcome_message("RaceBot", 17, False) == (
        "RaceBot is live. The entries are closed and the treadmill appears emotionally ready."
    )


def test_build_welcome_message_wraps_template_cycle():
    template_count = len(trackracerbot.WELCOME_MESSAGE_TEMPLATES)

    assert trackracerbot.build_welcome_message("RaceBot", template_count, True) == (
        "RaceBot is here. The treadmill is moving, the cars are confused, and entries are open."
    )


def test_build_costreaming_status_message_reports_registration_state():
    assert trackracerbot.build_costreaming_status_message(True) == (
        "Costreaming mode enabled. Reading the chat. Races are open currently."
    )
    assert trackracerbot.build_costreaming_status_message(False) == (
        "Costreaming mode enabled. Reading the chat. Races are closed currently."
    )


def test_build_signup_reminder_message_rotates_cleaned_templates():
    assert trackracerbot.build_signup_reminder_message(12, 0) == (
        "Entries are still open. Type !race before the treadmill starts judging the room."
    )
    assert trackracerbot.build_signup_reminder_message(12, 1) == (
        "Race control is hearing a lot of silence and seeing a lot of empty grid spots. !race gets you in."
    )
    assert trackracerbot.build_signup_reminder_message(12, 11) == (
        "Race control is still taking entries. Don't make the treadmill race itself."
    )
    assert trackracerbot.build_signup_reminder_message(12, 36) == (
        'Registration is still live. Enter now before someone says "last call" like this is a real sport.'
    )


def test_should_send_signup_reminder_requires_open_registration_and_idle_time():
    assert trackracerbot.should_send_signup_reminder(
        now=400.0,
        last_activity_at=100.0,
        reminder_sent=True,
        is_registration_open=True,
        entry_count=10,
        interval_seconds=60.0,
    )
    assert not trackracerbot.should_send_signup_reminder(
        now=400.0,
        last_activity_at=100.0,
        reminder_sent=False,
        is_registration_open=True,
        entry_count=10,
        interval_seconds=60.0,
    )
    assert not trackracerbot.should_send_signup_reminder(
        now=159.0,
        last_activity_at=100.0,
        reminder_sent=True,
        is_registration_open=True,
        entry_count=10,
        interval_seconds=60.0,
    )
    assert not trackracerbot.should_send_signup_reminder(
        now=400.0,
        last_activity_at=100.0,
        reminder_sent=True,
        is_registration_open=False,
        entry_count=10,
        interval_seconds=60.0,
    )
    assert not trackracerbot.should_send_signup_reminder(
        now=400.0,
        last_activity_at=100.0,
        reminder_sent=True,
        is_registration_open=True,
        entry_count=trackracerbot.MAX_ENTRIES,
        interval_seconds=60.0,
    )
    assert not trackracerbot.should_send_signup_reminder(
        now=400.0,
        last_activity_at=None,
        reminder_sent=True,
        is_registration_open=True,
        entry_count=10,
        interval_seconds=60.0,
    )


@pytest.mark.asyncio
async def test_send_signup_reminder_if_idle_queues_message_and_resets_idle_timer(monkeypatch):
    queue = trackracerbot.asyncio.Queue()
    trackracerbot.reset_response_rotation()
    trackracerbot.entry_queue.clear()
    trackracerbot.entry_queue.extend(f"racer_{index}" for index in range(10))
    monkeypatch.setattr(trackracerbot, "twitch_message_queue", queue)
    monkeypatch.setattr(trackracerbot, "twitch_channel_ref", object())
    monkeypatch.setattr(trackracerbot, "registration_open", True)
    monkeypatch.setattr(trackracerbot, "signup_reminder_interval_seconds", 60.0)
    monkeypatch.setattr(trackracerbot, "last_signup_activity_at", 100.0)
    monkeypatch.setattr(trackracerbot, "signup_reminder_pending", True)

    await trackracerbot.send_signup_reminder_if_idle(160.0)

    assert queue.get_nowait() == (
        "Entries are still open. Type !race before the treadmill starts judging the room."
    )
    assert trackracerbot.signup_reminder_pending is False


@pytest.mark.asyncio
async def test_send_signup_reminder_if_idle_sends_only_once_until_activity(monkeypatch):
    queue = trackracerbot.asyncio.Queue()
    trackracerbot.reset_response_rotation()
    trackracerbot.entry_queue.clear()
    monkeypatch.setattr(trackracerbot, "twitch_message_queue", queue)
    monkeypatch.setattr(trackracerbot, "twitch_channel_ref", object())
    monkeypatch.setattr(trackracerbot, "registration_open", True)
    monkeypatch.setattr(trackracerbot, "signup_reminder_interval_seconds", 60.0)
    monkeypatch.setattr(trackracerbot, "last_signup_activity_at", 100.0)
    monkeypatch.setattr(trackracerbot, "signup_reminder_pending", True)

    await trackracerbot.send_signup_reminder_if_idle(160.0)
    await trackracerbot.send_signup_reminder_if_idle(1000.0)

    assert queue.get_nowait() == (
        "Entries are still open. Type !race before the treadmill starts judging the room."
    )
    assert queue.empty()


@pytest.mark.asyncio
async def test_send_welcome_message_queues_twitch_chat_message(monkeypatch):
    queue = trackracerbot.asyncio.Queue()
    trackracerbot.reset_response_rotation()
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


@pytest.mark.asyncio
async def test_send_welcome_message_queues_closed_registration_welcome(monkeypatch):
    queue = trackracerbot.asyncio.Queue()
    trackracerbot.reset_response_rotation()
    monkeypatch.setattr(trackracerbot, "twitch_message_queue", queue)
    monkeypatch.setattr(trackracerbot, "twitch_channel_ref", object())
    monkeypatch.setattr(trackracerbot, "BOT_NAME", "RaceBot")
    monkeypatch.setattr(trackracerbot, "registration_open", False)

    await trackracerbot.send_welcome_message()

    assert await queue.get() == (
        "RaceBot is here. The treadmill is moving, the cars are confused, and entries are closed."
    )
    assert queue.get_nowait() == (
        "Costreaming mode enabled. Reading the chat. Races are closed currently."
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


def test_bot_state_round_trips_submission_stats(tmp_path, monkeypatch):
    state_file = tmp_path / "bot-state.json"
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    trackracerbot.entry_queue.clear()
    trackracerbot.reset_submission_stats(123.5)
    trackracerbot.submission_stats["accepted_entries"] = 7
    trackracerbot.submission_stats["twitch_entries"] = 4
    trackracerbot.submission_stats["reported"] = False

    trackracerbot.write_registration_state()
    trackracerbot.reset_submission_stats(None, persist=False)
    trackracerbot.load_registration_state()

    assert trackracerbot.submission_stats == {
        "started_at": 123.5,
        "accepted_entries": 7,
        "twitch_entries": 4,
        "reported": False,
    }


def test_registration_state_closes_when_restored_queue_is_full(tmp_path, monkeypatch):
    state_file = tmp_path / "bot-state.json"
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    trackracerbot.entry_queue.clear()
    trackracerbot.entry_queue.extend(
        f"racer_{index}" for index in range(trackracerbot.MAX_ENTRIES)
    )
    state_file.write_text('{"registration_open": true}', encoding="utf-8")

    trackracerbot.load_registration_state()

    assert not trackracerbot.registration_open


def test_set_registration_open_cannot_open_full_queue(tmp_path, monkeypatch):
    state_file = tmp_path / "bot-state.json"
    monkeypatch.setattr(trackracerbot, "bot_state_file_abs", str(state_file))
    trackracerbot.entry_queue.clear()
    trackracerbot.entry_queue.extend(
        f"racer_{index}" for index in range(trackracerbot.MAX_ENTRIES)
    )

    trackracerbot.set_registration_open(True)

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
