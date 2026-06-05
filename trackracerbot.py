from dotenv import load_dotenv
import os
import collections
import itertools
import threading
import asyncio
import time

from twitchio.ext import commands
from twitchio.message import Message as TwitchMessage

from googleapiclient.discovery import build
import datetime
from dateutil.parser import parse
import pytz

import websockets
import json
import re
import race_history

# Load the values from the .env file
load_dotenv()

# Use the values in the app
client_id = os.getenv('TWITCH_CLIENT_ID')
client_secret = os.getenv('TWITCH_CLIENT_SECRET')
access_token = os.getenv('TWITCH_ACCESS_TOKEN')
refresh_token = os.getenv('TWITCH_REFRESH_TOKEN')
TWITCH_CHANNEL = os.getenv('TWITCH_CHANNEL')
# TWITCH_CHANNEL = "2BeerMinimumRacing"
BOT_NAME = os.getenv('TWITCH_BOT_NAME')
api_key = os.getenv('YOUTUBE_API_KEY')
youtube_video_id = os.getenv('YOUTUBE_LIVE_VIDEO_ID')
entry_file = os.getenv('ENTRY_FILE')
CHAT_CAPTURE_FILE = os.getenv("CHAT_CAPTURE_FILE", "")

# Create a queue for storing the usernames
entry_queue = collections.deque()

# Variable for absolute path to Entry File
entry_file_abs = ""
if entry_file is None:
    entry_file = "entries.txt"

# Set the absolute path to the savefile
entry_file_abs = os.path.abspath(entry_file)
bot_state_file = os.getenv("BOT_STATE_FILE")
if bot_state_file is None:
    bot_state_file = os.path.join(os.path.dirname(entry_file_abs), "bot-state.json")
bot_state_file_abs = os.path.abspath(bot_state_file)
race_history_db = os.getenv("RACE_HISTORY_DB")
if race_history_db is None:
    race_history_db = os.path.join(
        os.path.dirname(entry_file_abs), "race-history.sqlite3"
    )
race_history_db_abs = os.path.abspath(race_history_db)

# Set maximum number of entries
MAX_ENTRIES = 30
registration_open = True

submission_stats = {
    "started_at": None,
    "accepted_entries": 0,
    "twitch_entries": 0,
    "reported": False,
}
submission_window = {
    "entries_opened_at_utc": None,
    "entries_closed_at_utc": None,
}

# Message queue for Twitch chat to handle rate limiting
# Will be initialized when Bot is ready (needs event loop)
twitch_message_queue = None
twitch_channel_ref = None  # Will be set when bot is ready

# Rate limiting: Twitch allows ~20 messages per 30 seconds for regular users
# We'll be conservative and send 1 message per 1.5 seconds (20 per 30s)
MESSAGE_RATE_LIMIT = 1.5  # seconds between messages
signup_reminder_interval_seconds = float(
    os.getenv("SIGNUP_REMINDER_INTERVAL_SECONDS", "60")
)
last_signup_activity_at = None
signup_reminder_pending = True

ENTRY_COMMANDS = ("!race", "!play", "!enter", "!join")
ENTRY_EMOTE_PREFIXES = (
    "artmannJudy",
    "x100pr3Hndoclap52",
    "x2beerShrek",
    "x2beerRace",
    "avoidr3Hotdogman",
    "spacec122GoodVibes",
    "artmannNatmar",
    "artmannOhyeah",
)

COMMAND_COMMANDS = "commands"
COMMAND_ENTRY = "entry"
COMMAND_START = "start"
COMMAND_OPEN_ENTRIES = "open_entries"
COMMAND_CLOSE_ENTRIES = "close_entries"
COMMAND_CLEAR_ENTRIES = "clear_entries"
COMMAND_ENTRIES = "entries"
COMMAND_ENTRY_LOOKUP = "entry_lookup"
COMMAND_WINNER = "winner"
COMMAND_SET_LAST_WINNER = "set_last_winner"
COMMAND_LEADERBOARD = "leaderboard"
COMMAND_STATS = "stats"
COMMAND_CAR_STATS = "car_stats"
COMMAND_CAR_LEADERBOARD = "car_leaderboard"
COMMAND_STREAM_RACE_STATS = "stream_race_stats"
COMMAND_UNKNOWN = "unknown"

COMMANDS_COMMAND = "!commands"
START_COMMAND = "!start"
OPEN_ENTRIES_COMMAND = "!openentries"
CLOSE_ENTRIES_COMMAND = "!closeentries"
CLEAR_ENTRIES_COMMAND = "!clearentries"
ENTRIES_COMMAND = "!entries"
ENTRY_LOOKUP_COMMAND = "!entry"
WINNER_COMMAND = "!winner"
SET_LAST_WINNER_COMMAND = "!setlastwinner"
LEADERBOARD_COMMAND = "!leaderboard"
STATS_COMMAND = "!stats"
CAR_STATS_COMMAND = "!carstats"
CAR_LEADERBOARD_COMMAND = "!carleaderboard"
STREAM_RACE_STATS_COMMAND = "!streamracestats"

LEADERBOARD_RANK_MARKERS = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣")

ENTRY_RESPONSE_TEMPLATES = (
    "You're in, {author}. You're car #{position}.",
    "Locked in, {author}. You're car #{position}.",
    "Added to the grid, {author}. You're car #{position}.",
    "You're on the list, {author}. Car #{position} is yours.",
    "Registered, {author}. You've got car #{position}.",
    "Welcome to the queue, {author}. You're car #{position}.",
    "Got you, {author}. You're in car #{position}.",
    "Grid slot claimed, {author}. You're car #{position}.",
)

DUPLICATE_ENTRY_RESPONSE_TEMPLATES = (
    "You're already in, {author}. You're car #{position}.",
    "You're on the grid already, {author}. Car #{position} is yours.",
    "Hold tight, {author}. You're already car #{position}.",
    "Already got you, {author}. You're in car #{position}.",
    "No need to re-enter, {author}. You're car #{position}.",
    "You're still locked in, {author}. Car #{position} is set.",
    "Duplicate ignored, {author}. You're already car #{position}.",
    "You're covered, {author}. Car #{position} is yours.",
)

SIGNUP_REMINDER_TEMPLATES = (
    "Entries are still open. Type !race before the treadmill starts judging the room.",
    "Race control is hearing a lot of silence and seeing a lot of empty grid spots. !race gets you in.",
    "The belt is warm, the grid is lonely, and your car has not yet made a terrible decision. Type !race.",
    "This is your reminder that !race exists, and so does glory on moving rubber.",
    "Registration remains open. The treadmill is patient, but only because it has no concept of mercy.",
    "The race queue is still accepting brave little machines. Type !race and become part of the incident.",
    "We have open spots on the grid and a treadmill with nothing better to do. !race to enter.",
    "The silence in registration is suspicious. Somebody type !race before we start inspecting setups.",
    "Entries are open. This is not the time to be responsible.",
    "The grid has room. The belt has attitude. Type !race.",
    "Somewhere out there is a car that deserves to fly off a treadmill. Type !race and nominate it.",
    "Race control is still taking entries. Don't make the treadmill race itself.",
    "The list is open, the track is moving, and the excuses are still free. !race to join.",
    "There are empty grid slots, which means several of you are still pretending to have dignity.",
    "Type !race to enter. Or don't, and let someone else become treadmill folklore.",
    "Registration is still open. The fastest way to join is !race. The funniest way is also !race.",
    "We are moments away from organized belt-based nonsense. !race gets you on the list.",
    "The treadmill has been repurposed and it demands competitors. Type !race.",
    "There is still time to enter before physics starts taking attendance.",
    "Race control has detected a lull. This is usually where someone makes a bad but entertaining choice.",
    "The entry list is looking a little too safe. Type !race and fix that.",
    "The grid is not full yet. That means your tiny car still has a chance to disappoint everyone.",
    "Registration remains open for cars, dreams, and suspicious engineering. !race to enter.",
    "The belt is idle enough to think. That is dangerous. Type !race.",
    "Open entries, open track, open question: who's brave enough to get thrown into treadmill history?",
    "This is the part where the quiet people suddenly become competitors. Type !race.",
    "The treadmill is warmed up. Your excuses can warm up later. !race to join.",
    "The field needs more victims. Respectfully. !race.",
    "Race control is accepting entries and emotional support vehicles. Type !race.",
    "There is still room on the list for one more bad idea with wheels.",
    "The grid is open. The treadmill is hungry. Chat is suspiciously quiet.",
    "Type !race now and give the announcer something irresponsible to say.",
    "We have empty slots and a moving track. This problem solves itself when you type !race.",
    "The entry window is still open. Do not let the responsible people win.",
    "This lull has been reviewed by race control and declared unacceptable. !race.",
    "The belt is standing by for competitors. Or sacrifices. The paperwork is unclear.",
    'Registration is still live. Enter now before someone says "last call" like this is a real sport.',
    "The race list has space. The treadmill has opinions. !race to join.",
    "This is your chance to become a name on a very strange leaderboard.",
    "Race control would like to remind chat that watching is safer, but entering is funnier.",
    "The grid could use more chaos. Type !race and bring your own problem.",
    "Open registration continues. Please enter before the treadmill gets bored and starts picking favorites.",
    "Some of you are lurking like your car wouldn't immediately become content. Type !race.",
    "The belt is ready. The bot is ready. The question is whether chat has courage.",
    "Entries remain open. This is treadmill racing, not jury duty. Participation is encouraged.",
    "Type !race to join the grid and receive absolutely no guarantee of dignity.",
    "The race queue has room for more tiny cars and bigger mistakes.",
    "The treadmill has not yet claimed enough dreams. !race to assist.",
    "Registration is still open. The only wrong move is pretending you're above this.",
    "The grid needs more names. The belt needs more business. Type !race.",
    "This is a friendly reminder from race control: !race puts you in the madness.",
    "The entry list is open, and so is the possibility of becoming a cautionary tale.",
    "Quiet chat means empty grid. Empty grid means the treadmill wins. Type !race.",
    "The belt is spinning spiritually, even if not physically. It wants competitors.",
    "Type !race and let your car experience the most questionable racetrack in the room.",
    "Registration remains open for all brave, doomed, or overconfident entries.",
    "The list is still open. The treadmill has been staring at us for too long.",
    "Race control has noticed several potential cowards in the stands. !race may correct this.",
    "This is the awkward silence before someone enters and immediately regrets it.",
    "The grid is open. The drama is under capacity. Type !race.",
    "Entries are still open. Somebody give this treadmill a reason to believe.",
    "The queue needs more names before we can call this a proper disaster.",
    "Type !race and join the only race where the track does cardio for you.",
    "The entry window remains open. Don't let the belt sit there unemployed.",
    "Race control is requesting more cars for scientific and comedic purposes.",
    "The grid is not full, which means glory is still available at a questionable discount.",
    "Type !race before someone else takes your spot in treadmill history.",
    "The treadmill is accepting challengers. Chat is accepting peer pressure.",
    "Open slots remain. That is not a warning. That is an invitation.",
    "The race list is looking polite. We need less polite. Type !race.",
    "Registration is open and the belt has no respect for hesitation.",
    "This is your low-pressure opportunity to make a high-speed mistake.",
    "The treadmill is ready to turn someone's setup into a lesson. !race to volunteer.",
    "Race control is still awake, somehow. Type !race and make it worth it.",
    "The grid needs more contenders, pretenders, and rolling question marks.",
    "Entries are open. Become part of the show before the show becomes part of you.",
    "The silence is strong, but the lure of tiny car chaos is stronger. !race.",
    "Type !race and find out if your car is fast, stable, or decorative.",
    "Registration is still open. The belt waits for no one, except currently everyone.",
    "The track is ready. The bot is nagging. The grid has room.",
    "Somebody type !race before we start interviewing the treadmill.",
    "The entry list has vacancies and the announcer has dangerous levels of free time.",
    "This lull brought to you by hesitation. End it with !race.",
    "Race control is still taking entries. Pride is optional. Wheels are preferred.",
    "The treadmill has been converted into a racetrack and somehow you're still not entered.",
    "Type !race and become part of a motorsport format your insurance agent would not understand.",
    "Open grid spots remain for anyone brave enough to challenge moving rubber.",
    "The belt is bored, the bot is watching, and chat has unfinished business.",
    "Registration is still live. Enter now and let the treadmill sort out the details.",
    "The list needs more names before we can properly blame physics.",
    "Type !race. Worst case, you become content. Best case, you also become content.",
    "Race control is asking nicely before it starts asking like a disappointed crew chief.",
    "Entries are still open. This is the part where legends, cowards, and toy cars separate themselves.",
    "The grid is hungry. The belt is mean. The command is !race.",
)

START_RESPONSE_TEMPLATES = (
    "Starting grid locked: {lineup}",
    "Rolling out with: {lineup}",
    "Race lineup is set: {lineup}",
    "Sending these racers: {lineup}",
    "On the line: {lineup}",
    "Next race is ready for: {lineup}",
    "Grid is live: {lineup}",
    "Race call: {lineup}",
)

WELCOME_MESSAGE_TEMPLATES = (
    "[botname] is here. The treadmill is moving, the cars are confused, and entries are {registration_status}.",
    "[botname] has arrived at race control. Please submit your tiny machines and oversized confidence.",
    "[botname] is online. I'm here to collect entries and pretend this is a sanctioned event.",
    "[botname] has joined the paddock. The track is a treadmill, which already answers several questions.",
    "[botname] is here. If your car has wheels and a dream, get it entered.",
    "[botname] has arrived. The racing surface is technically exercise equipment, but we're moving forward.",
    "[botname] is live. Entries are {registration_status} for whatever this beautiful motorsport mistake is.",
    "[botname] just walked into race control. The grid is forming, the treadmill is humming, and nobody is fully prepared.",
    "[botname] is here. Tonight we find out which vehicle has speed, courage, and poor traction management.",
    "[botname] has joined. Please line up your tiny race cars and enormous expectations.",
    "[botname] is now accepting entries. This is not Formula 1, but the paperwork is somehow worse.",
    "[botname] has arrived at the timing booth. I assume the timing booth is just a guy near a treadmill.",
    "[botname] is here. The cars are small, the drama is real, and the track refuses to sit still.",
    "[botname] has entered the chat. I'll be handling entries for the world's least OSHA-approved motorsport.",
    "[botname] is online. The treadmill has been converted from fitness equipment to destiny equipment.",
    "[botname] is here. If your vehicle can survive belt speed and public judgment, send it in.",
    "[botname] has joined race control. We have a moving track, questionable engineering, and a crowd that wants answers.",
    "[botname] is live. The entries are {registration_status} and the treadmill appears emotionally ready.",
    "[botname] has arrived. This is racing, technically, and that is good enough for me.",
    "[botname] is here. Please register your car before it becomes track debris.",
    "[botname] has joined. The paddock is open, the belt is ready, and someone's about to learn about friction.",
    "[botname] is online. I'm collecting entries for tiny cars doing big dumb hero stuff.",
    "[botname] has arrived. The track moves, the cars cope, and I make announcements like this is normal.",
    "[botname] is here. Get your entries in before the treadmill achieves sentience.",
)

REGISTRATION_CLOSED_RESPONSE = (
    "Grid is locked, {author}."
)

start_response_counter = itertools.count()
duplicate_entry_response_counter = itertools.count()
welcome_message_counter = itertools.count()
signup_reminder_counter = itertools.count()


def is_entry_message(message: str) -> bool:
    message_lower = message.lower()
    return message_lower.startswith(ENTRY_COMMANDS) or message.startswith(ENTRY_EMOTE_PREFIXES)


def is_commands_message(message: str) -> bool:
    return message.lower().startswith(COMMANDS_COMMAND)


def is_start_message(message: str) -> bool:
    return message.lower().startswith(START_COMMAND)


def is_open_entries_message(message: str) -> bool:
    return message.lower().startswith(OPEN_ENTRIES_COMMAND)


def is_close_entries_message(message: str) -> bool:
    return message.lower().startswith(CLOSE_ENTRIES_COMMAND)


def is_clear_entries_message(message: str) -> bool:
    return message.lower().startswith(CLEAR_ENTRIES_COMMAND)


def is_entries_message(message: str) -> bool:
    return message.lower().startswith(ENTRIES_COMMAND)


def is_entry_lookup_message(message: str) -> bool:
    message_lower = message.lower()
    return message_lower == ENTRY_LOOKUP_COMMAND or message_lower.startswith(
        ENTRY_LOOKUP_COMMAND + " "
    )


def is_exact_or_space_command(message: str, command: str) -> bool:
    message_lower = message.lower()
    return message_lower == command or message_lower.startswith(command + " ")


def is_winner_message(message: str) -> bool:
    return is_exact_or_space_command(message, WINNER_COMMAND)


def is_set_last_winner_message(message: str) -> bool:
    return is_exact_or_space_command(message, SET_LAST_WINNER_COMMAND)


def is_leaderboard_message(message: str) -> bool:
    return is_exact_or_space_command(message, LEADERBOARD_COMMAND)


def is_stats_message(message: str) -> bool:
    return is_exact_or_space_command(message, STATS_COMMAND)


def is_car_stats_message(message: str) -> bool:
    return is_exact_or_space_command(message, CAR_STATS_COMMAND)


def is_car_leaderboard_message(message: str) -> bool:
    return is_exact_or_space_command(message, CAR_LEADERBOARD_COMMAND)


def is_stream_race_stats_message(message: str) -> bool:
    return is_exact_or_space_command(message, STREAM_RACE_STATS_COMMAND)


def classify_message(message: str) -> str:
    if is_commands_message(message):
        return COMMAND_COMMANDS
    if is_entry_lookup_message(message):
        return COMMAND_ENTRY_LOOKUP
    if is_winner_message(message):
        return COMMAND_WINNER
    if is_set_last_winner_message(message):
        return COMMAND_SET_LAST_WINNER
    if is_leaderboard_message(message):
        return COMMAND_LEADERBOARD
    if is_stats_message(message):
        return COMMAND_STATS
    if is_car_stats_message(message):
        return COMMAND_CAR_STATS
    if is_car_leaderboard_message(message):
        return COMMAND_CAR_LEADERBOARD
    if is_stream_race_stats_message(message):
        return COMMAND_STREAM_RACE_STATS
    if is_entry_message(message):
        return COMMAND_ENTRY
    if is_start_message(message):
        return COMMAND_START
    if is_open_entries_message(message):
        return COMMAND_OPEN_ENTRIES
    if is_close_entries_message(message):
        return COMMAND_CLOSE_ENTRIES
    if is_clear_entries_message(message):
        return COMMAND_CLEAR_ENTRIES
    if is_entries_message(message):
        return COMMAND_ENTRIES
    return COMMAND_UNKNOWN


def reset_response_rotation() -> None:
    global duplicate_entry_response_counter, start_response_counter
    global welcome_message_counter, signup_reminder_counter
    duplicate_entry_response_counter = itertools.count()
    start_response_counter = itertools.count()
    welcome_message_counter = itertools.count()
    signup_reminder_counter = itertools.count()


def display_car_number(position: int) -> int:
    if position == 29:
        return 69
    return position


def find_entry_by_display_number(entries, display_number: int):
    for index, name in enumerate(entries, start=1):
        if display_car_number(index) == display_number:
            return name, index
    return None


def normalize_entry_lookup_name(search_text: str) -> str:
    return search_text.strip().lstrip("@").lower()


def find_entry_by_name(entries, search_text: str):
    normalized_search = normalize_entry_lookup_name(search_text)
    for index, name in enumerate(entries, start=1):
        if name.lower() == normalized_search:
            return name, index
    return None


def build_entry_lookup_response(search_text: str, entries) -> str:
    query = search_text.strip()
    if not query:
        return "Usage: !entry {number or name}"

    if query.isdigit():
        display_number = int(query)
        result = find_entry_by_display_number(entries, display_number)
        if result is None:
            return f"No entry found for car #{display_number}."

        name, _position = result
        return f"Car #{display_number} is {name}."

    result = find_entry_by_name(entries, query)
    if result is None:
        return f"No entry found for {query}."

    name, position = result
    return f"{name} is car #{display_car_number(position)}."


def build_own_entry_lookup_response(author: str, entries) -> str:
    result = find_entry_by_name(entries, author)
    if result is None:
        return f"{author}, you're not in this race. Maybe the next one gets your moment."

    name, position = result
    return f"{name} is car #{display_car_number(position)}."


def build_entry_response(author: str, position: int) -> str:
    template = ENTRY_RESPONSE_TEMPLATES[(position - 1) % len(ENTRY_RESPONSE_TEMPLATES)]
    return template.format(author=author, position=display_car_number(position))


def build_duplicate_entry_response(author: str, position: int, rotation_index: int) -> str:
    template = DUPLICATE_ENTRY_RESPONSE_TEMPLATES[
        rotation_index % len(DUPLICATE_ENTRY_RESPONSE_TEMPLATES)
    ]
    return template.format(author=author, position=display_car_number(position))


def build_start_response(lineup_names, rotation_index: int) -> str:
    lineup = ", ".join(name.lower() for name in lineup_names)
    template = START_RESPONSE_TEMPLATES[rotation_index % len(START_RESPONSE_TEMPLATES)]
    return template.format(lineup=lineup)


def build_registration_closed_response(author: str) -> str:
    return REGISTRATION_CLOSED_RESPONSE.format(author=author)


def format_racer_stats(stats: dict) -> str:
    return (
        f"{stats['name']}: {stats['wins']}W / "
        f"{stats['total_races']}R / {stats['win_percentage']:.1f}%."
    )


def format_inline_racer_stats(stats: dict) -> str:
    return f"{stats['wins']}W / {stats['total_races']}R / {stats['win_percentage']:.1f}%"


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


def build_winner_recorded_response(prefix: str, result: dict) -> str:
    stats = result["stats"]
    return f"{prefix}: {result['winner_name']}. {format_inline_racer_stats(stats)}."


def build_leaderboard_response(leaderboard: list[dict]) -> str:
    if not leaderboard:
        return "No completed winners yet."
    parts = []
    for index, stats in enumerate(leaderboard[:5], start=1):
        parts.append(
            f"{leaderboard_rank_marker(index)} {stats['name']} "
            f"{stats['wins']}W/{stats['total_races']}R "
            f"{stats['win_percentage']:.1f}%"
        )
    return "Top winners: " + " ".join(parts) + "."


def leaderboard_rank_marker(index: int) -> str:
    if 1 <= index <= len(LEADERBOARD_RANK_MARKERS):
        return LEADERBOARD_RANK_MARKERS[index - 1]
    return f"{index}."


def parse_car_stats_display_number(query: str) -> int | None:
    stripped_query = query.strip()
    if not stripped_query.isdecimal():
        return None
    display_number = int(stripped_query)
    if display_number <= 0:
        return None
    return display_number


def build_car_stats_response(stats: dict | None, display_number: int) -> str:
    if stats is None:
        return f"No races recorded for car #{display_number}."

    response = (
        f"Car #{stats['display_number']}: {stats['wins']}W / "
        f"{stats['total_races']}R / {stats['win_percentage']:.1f}%."
    )
    if stats["best_driver"] is not None:
        response += f" Best driver: {stats['best_driver']} {stats['best_driver_wins']}W."
    if stats["last_win"] is not None:
        response += f" Last win: {stats['last_win']}."
    return response


def build_car_leaderboard_response(leaderboard: list[dict]) -> str:
    if not leaderboard:
        return "No completed car winners yet."
    parts = []
    for index, stats in enumerate(leaderboard[:5], start=1):
        parts.append(
            f"{leaderboard_rank_marker(index)} #{stats['display_number']} "
            f"{stats['wins']}W/{stats['total_races']}R "
            f"{stats['win_percentage']:.1f}%"
        )
    return "Top cars: " + " ".join(parts) + "."


def stream_race_stats_cutoff(
    now_utc: datetime.datetime | None = None,
    local_timezone=None,
) -> datetime.datetime:
    now = now_utc or datetime.datetime.now(datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    local_tz = local_timezone or datetime.datetime.now().astimezone().tzinfo
    local_now = now.astimezone(local_tz)
    local_noon = local_now.replace(
        hour=12,
        minute=0,
        second=0,
        microsecond=0,
    )
    if local_now < local_noon:
        local_noon -= datetime.timedelta(days=1)
    return local_noon.astimezone(datetime.timezone.utc)


def format_stream_winners(winners: list[dict]) -> str:
    if not winners:
        return "none"
    parts = []
    for index, winner in enumerate(winners, start=1):
        parts.append(
            f"{leaderboard_rank_marker(index)} "
            f"{winner['name']} #{winner['display_number']}"
        )
    return " ".join(parts)


def format_stream_leader_parts(leaders: list[dict], label_key: str) -> str:
    if not leaders:
        return "none"
    parts = []
    for leader in leaders[:3]:
        if label_key == "display_number":
            label = f"#{leader[label_key]}"
        else:
            label = leader[label_key]
        parts.append(f"{label} {leader['wins']}W")
    return " / ".join(parts)


def build_stream_race_stats_messages(summary: dict) -> list[str]:
    messages = [
        (
            "Stream Race Stats 🏁 "
            f"Races: {summary['total']} total / "
            f"{summary['completed']} completed / "
            f"{summary['pending']} pending / "
            f"{summary['skipped']} skipped "
            f"🏆 Winners: {format_stream_winners(summary['winners'])}"
        )
    ]

    if summary["completed"] > 0:
        messages.append(
            "Stream Leaders 🏆 "
            f"Drivers: {format_stream_leader_parts(summary['top_drivers'], 'name')} "
            f"🚗 Cars: {format_stream_leader_parts(summary['top_cars'], 'display_number')} "
            f"🎯 Unique winners: {summary['unique_winners']}"
        )

    return messages


def build_welcome_message(
    bot_name: str, rotation_index: int, is_registration_open: bool
) -> str:
    template = WELCOME_MESSAGE_TEMPLATES[
        rotation_index % len(WELCOME_MESSAGE_TEMPLATES)
    ]
    registration_status = "open" if is_registration_open else "closed"
    return template.format(registration_status=registration_status).replace(
        "[botname]", bot_name or "TrackRacerBot"
    )


def build_costreaming_status_message(is_registration_open: bool) -> str:
    status = "open" if is_registration_open else "closed"
    return (
        "Costreaming mode enabled. Reading the chat. "
        f"Races are {status} currently."
    )


def build_signup_reminder_message(remaining_slots: int, rotation_index: int) -> str:
    spot_word = "spot" if remaining_slots == 1 else "spots"
    template = SIGNUP_REMINDER_TEMPLATES[
        rotation_index % len(SIGNUP_REMINDER_TEMPLATES)
    ]
    return template.format(remaining_slots=remaining_slots, spot_word=spot_word)


def should_send_signup_reminder(
    now: float,
    last_activity_at: float,
    reminder_sent: bool,
    is_registration_open: bool,
    entry_count: int,
    interval_seconds: float,
) -> bool:
    return (
        interval_seconds > 0
        and reminder_sent
        and is_registration_open
        and entry_count < MAX_ENTRIES
        and last_activity_at is not None
        and now - last_activity_at >= interval_seconds
    )


def mark_signup_activity(monotonic_time: float) -> None:
    global last_signup_activity_at, signup_reminder_pending
    last_signup_activity_at = monotonic_time
    signup_reminder_pending = True


async def send_signup_reminder_if_idle(now: float) -> None:
    global signup_reminder_pending

    if not should_send_signup_reminder(
        now=now,
        last_activity_at=last_signup_activity_at,
        reminder_sent=signup_reminder_pending,
        is_registration_open=registration_open,
        entry_count=len(entry_queue),
        interval_seconds=signup_reminder_interval_seconds,
    ):
        return

    remaining_slots = MAX_ENTRIES - len(entry_queue)
    await print_everywhere(
        build_signup_reminder_message(
            remaining_slots,
            next(signup_reminder_counter),
        )
    )
    signup_reminder_pending = False


async def send_welcome_message() -> None:
    await print_everywhere(
        build_welcome_message(BOT_NAME, next(welcome_message_counter), registration_open)
    )
    await print_everywhere(build_costreaming_status_message(registration_open))


def write_registration_state() -> None:
    try:
        state_dir = os.path.dirname(bot_state_file_abs)
        if state_dir:
            os.makedirs(state_dir, exist_ok=True)

        with open(bot_state_file_abs, "w", encoding="utf-8") as state_file:
            json.dump(
                {
                    "registration_open": registration_open,
                    "submission_stats": submission_stats,
                    "submission_window": submission_window,
                },
                state_file,
            )
    except OSError as e:
        print(f"Could not write bot state: {e}")


def set_registration_open(is_open: bool, persist: bool = True) -> None:
    global registration_open
    registration_open = is_open and len(entry_queue) < MAX_ENTRIES
    if persist:
        write_registration_state()


def load_registration_state() -> None:
    global registration_open

    if not os.path.exists(bot_state_file_abs):
        registration_open = len(entry_queue) == 0
        return

    try:
        with open(bot_state_file_abs, encoding="utf-8") as state_file:
            state = json.load(state_file)
        registration_open = (
            bool(state.get("registration_open", len(entry_queue) == 0))
            and len(entry_queue) < MAX_ENTRIES
        )
        loaded_submission_stats = state.get("submission_stats", {})
        if isinstance(loaded_submission_stats, dict):
            submission_stats["started_at"] = loaded_submission_stats.get("started_at")
            submission_stats["accepted_entries"] = int(
                loaded_submission_stats.get("accepted_entries", 0)
            )
            submission_stats["twitch_entries"] = int(
                loaded_submission_stats.get("twitch_entries", 0)
            )
            submission_stats["reported"] = bool(
                loaded_submission_stats.get("reported", False)
            )
        loaded_submission_window = state.get("submission_window", {})
        if isinstance(loaded_submission_window, dict):
            submission_window["entries_opened_at_utc"] = loaded_submission_window.get(
                "entries_opened_at_utc"
            )
            submission_window["entries_closed_at_utc"] = loaded_submission_window.get(
                "entries_closed_at_utc"
            )
    except (OSError, ValueError, TypeError) as e:
        print(f"Could not read bot state: {e}")
        registration_open = len(entry_queue) == 0


def is_moderator_message_source(twitch_message: TwitchMessage = None, youtube_message=None) -> bool:
    is_mod = False
    if twitch_message is not None and twitch_message.author is not None:
        is_mod = twitch_message.author.is_mod
    if youtube_message is not None and youtube_message["authorDetails"] is not None:
        is_mod = (
            youtube_message["authorDetails"]["isChatOwner"]
            or youtube_message["authorDetails"]["isChatModerator"]
        )
    return is_mod


def is_chat_capture_enabled() -> bool:
    return bool(CHAT_CAPTURE_FILE)


def build_twitch_capture_record(
    message: str,
    author: str,
    command: str,
    is_mod: bool,
    bot_outputs: list[str],
    twitch_message: TwitchMessage = None,
) -> dict:
    if twitch_message is None:
        return {}

    return {
        "source": "twitch",
        "author": author,
        "message": message,
        "classification": command,
        "is_mod": is_mod,
        "bot_outputs": list(bot_outputs),
    }


def write_chat_capture_record(record: dict) -> None:
    if not is_chat_capture_enabled() or not record:
        return

    try:
        capture_dir = os.path.dirname(CHAT_CAPTURE_FILE)
        if capture_dir:
            os.makedirs(capture_dir, exist_ok=True)

        with open(CHAT_CAPTURE_FILE, "a", encoding="utf-8") as capture_file:
            capture_file.write(json.dumps(record) + "\n")
    except OSError as e:
        print(f"Could not write chat capture record: {e}")


def reset_submission_stats(started_at: float = None, persist: bool = True) -> None:
    submission_stats["started_at"] = started_at
    submission_stats["accepted_entries"] = 0
    submission_stats["twitch_entries"] = 0
    submission_stats["reported"] = False
    if persist:
        write_registration_state()


def mark_entries_opened(opened_at_utc: str = None, persist: bool = True) -> None:
    submission_window["entries_opened_at_utc"] = opened_at_utc or race_history.utc_now_iso()
    submission_window["entries_closed_at_utc"] = None
    if persist:
        write_registration_state()


def mark_entries_closed(closed_at_utc: str = None, persist: bool = True) -> None:
    submission_window["entries_closed_at_utc"] = closed_at_utc or race_history.utc_now_iso()
    if persist:
        write_registration_state()


def format_elapsed_time(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    remaining_seconds = total_seconds % 60

    if hours:
        return f"{hours}h {minutes}m {remaining_seconds}s"
    if minutes:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


def record_submission_entry(twitch_message: TwitchMessage = None) -> None:
    if submission_stats["started_at"] is None or submission_stats["reported"]:
        return

    submission_stats["accepted_entries"] += 1
    if twitch_message is not None:
        submission_stats["twitch_entries"] += 1
    write_registration_state()


def build_submission_stats_message(finished_at: float) -> str:
    elapsed = format_elapsed_time(finished_at - submission_stats["started_at"])
    accepted_entries = submission_stats["accepted_entries"]
    twitch_entries = submission_stats["twitch_entries"]
    twitch_percentage = (
        twitch_entries / accepted_entries * 100
        if accepted_entries
        else 0
    )

    return (
        f"Entry list filled in {elapsed}. "
        f"Twitch entries: {twitch_percentage:.1f}% "
        f"({twitch_entries}/{accepted_entries})."
    )


def should_report_submission_stats() -> bool:
    return (
        submission_stats["started_at"] is not None
        and not submission_stats["reported"]
        and len(entry_queue) >= MAX_ENTRIES
    )


def clear_queue():
    # Clear the queue
    entry_queue.clear()
    bang_out_queue_to_file(entry_file_abs)

# Handle incoming chat messages (passed data from twitch or Youtube)
async def handle_message(message: str, author: str, twitch_message: TwitchMessage = None, youtube_message = None):
    # Check if we have a race entry
    # !race !enter !join - add to queue
    # !startrace - remove the first MAX_ENTRIES from queue
    # !clearentries - clear list of entries
    # !entries - print entries in race

    is_mod = is_moderator_message_source(twitch_message=twitch_message, youtube_message=youtube_message)
    command = classify_message(message)
    capture_outputs = []

    async def respond(logmessage: str):
        capture_outputs.append(logmessage)
        await print_everywhere(logmessage, twitch_message=twitch_message)

    if command == COMMAND_COMMANDS:
        commands_message = (
            "Available commands: !play !entries !winner !leaderboard !stats "
            "!carstats !carleaderboard !streamracestats"
        )
        if is_mod:
            commands_message += (
                " // Mod Commands: !start !openentries !closeentries !clearentries "
                "!winner <number|name> !setlastwinner"
            )
        await respond(commands_message)

    elif command == COMMAND_ENTRY_LOOKUP:
        search_text = message[len(ENTRY_LOOKUP_COMMAND):].strip()
        if search_text:
            await respond(build_entry_lookup_response(search_text, entry_queue))
        else:
            await respond(build_own_entry_lookup_response(author, entry_queue))

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

    elif command == COMMAND_CAR_STATS:
        car_stats_query = message[len(CAR_STATS_COMMAND):].strip()
        display_number = parse_car_stats_display_number(car_stats_query)
        if display_number is None:
            await respond("Usage: !carstats <number>")
        else:
            await respond(
                build_car_stats_response(
                    race_history.get_car_stats(race_history_db_abs, display_number),
                    display_number,
                )
            )

    elif command == COMMAND_CAR_LEADERBOARD:
        await respond(
            build_car_leaderboard_response(
                race_history.get_car_leaderboard(race_history_db_abs, limit=5)
            )
        )

    elif command == COMMAND_STREAM_RACE_STATS:
        cutoff = stream_race_stats_cutoff()
        cutoff_iso = cutoff if isinstance(cutoff, str) else cutoff.isoformat()
        summary = race_history.get_stream_race_summary(
            race_history_db_abs,
            cutoff_iso,
        )
        for response_message in build_stream_race_stats_messages(summary):
            await respond(response_message)

    if command == COMMAND_ENTRY:
        if not registration_open:
            await respond(build_registration_closed_response(author))
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

        if author in entry_queue:
            position = list(entry_queue).index(author) + 1
            await respond(
                build_duplicate_entry_response(
                    author,
                    position,
                    next(duplicate_entry_response_counter),
                )
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

        # Add to queue, or print full message
        if len(entry_queue) < MAX_ENTRIES:
            # Add to entry queue
            entry_queue.append(author)

            # Write to a file for the MAX_ENTRIES
            bang_out_queue_to_file(entry_file_abs)

            record_submission_entry(twitch_message=twitch_message)
            mark_signup_activity(time.monotonic())

            await respond(build_entry_response(author, len(entry_queue)))
            if should_report_submission_stats():
                await respond(build_submission_stats_message(time.monotonic()))
                submission_stats["reported"] = True
                write_registration_state()
        else:
            await respond("The list is full, " + author + ". Better luck next race!")

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

        pending_race_to_delete = None
        pending_race = race_history.get_latest_pending_race(race_history_db_abs)
        if pending_race is not None:
            pending_entries = race_history.get_race_entries(
                race_history_db_abs,
                pending_race["id"],
            )
            pending_lineup = [
                race_history.normalize_name(entry["name"]) for entry in pending_entries
            ]
            requested_lineup = [
                race_history.normalize_name(name) for name in lineup_names
            ]
            if pending_lineup == requested_lineup:
                pending_race_to_delete = pending_race["id"]
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

        mark_entries_closed(persist=False)
        race_history.start_race(
            race_history_db_abs,
            lineup_names,
            entries_opened_at_utc=submission_window["entries_opened_at_utc"],
            entries_closed_at_utc=submission_window["entries_closed_at_utc"],
            created_by=author,
        )
        if pending_race_to_delete is not None:
            race_history.delete_race(race_history_db_abs, pending_race_to_delete)
        await respond(build_start_response(lineup_names, next(start_response_counter)))
        set_registration_open(False, persist=False)
        write_registration_state()

    elif command == COMMAND_OPEN_ENTRIES and is_mod:
        set_registration_open(True, persist=False)
        mark_entries_opened(persist=False)
        mark_signup_activity(time.monotonic())
        write_registration_state()
        await respond("Entries are open.")

    elif command == COMMAND_CLOSE_ENTRIES and is_mod:
        set_registration_open(False, persist=False)
        mark_entries_closed(persist=False)
        write_registration_state()
        await respond("entries closed")
                
    elif command == COMMAND_CLEAR_ENTRIES and is_mod:
        # Clear the queue
        clear_queue()
        set_registration_open(True, persist=False)
        reset_submission_stats(time.monotonic(), persist=False)
        mark_entries_opened(persist=False)
        mark_signup_activity(time.monotonic())
        write_registration_state()
        await respond("All entries have been cleared.")

    elif command == COMMAND_ENTRIES:
        # Print the queue
        await respond("Race Entries: " + ", ".join(entry_queue))

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

def bang_out_queue_to_file(file):
    with open(file, 'w') as f:

        for element in entry_queue:
            # Write the element to the file, followed by a newline character
            f.write(element + '\n')

        if (len(entry_queue) < MAX_ENTRIES):
            # Iterate over a range of numbers from len(entry_queue) to MAX_ENTRIES
            for i in range(len(entry_queue),MAX_ENTRIES):
                f.write('\n')

# Function for printing the message in console, twitch, and youtube chats
async def print_everywhere(logmessage: str, twitch_message: TwitchMessage = None):
    # Print to local console
    print(logmessage)

    # Queue message for Twitch chat instead of sending immediately
    # This prevents rate limit errors
    global twitch_message_queue, twitch_channel_ref
    
    if twitch_message is not None:
        # Store channel reference for later use
        if twitch_channel_ref is None:
            twitch_channel_ref = twitch_message.channel
        
        # Add message to queue if it's initialized
        if twitch_message_queue is not None:
            await twitch_message_queue.put(logmessage)
        else:
            # Fallback: try to send directly if queue isn't ready yet
            try:
                await twitch_message.channel.send(logmessage)
            except Exception as e:
                print(f"Could not send message (queue not ready): {e}")
    elif twitch_channel_ref is not None and twitch_message_queue is not None:
        # We have a channel reference but no message object (e.g., from YouTube)
        await twitch_message_queue.put(logmessage)

    # TODO: Print this message in YT chat (can't -- api)

class Bot(commands.Bot):

    def __init__(self):
        super().__init__(token=access_token, client_id=client_id, nick=BOT_NAME, prefix='!', initial_channels=[TWITCH_CHANNEL])
        self._message_processor_task = None
        self._signup_reminder_task = None

    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')
        
        # Initialize message queue (needs event loop to exist)
        global twitch_message_queue, twitch_channel_ref
        if twitch_message_queue is None:
            twitch_message_queue = asyncio.Queue()
            print('Message queue initialized')
        
        # Store channel reference for message queue
        if self.connected_channels:
            twitch_channel_ref = self.connected_channels[0]
            print(f'Channel reference stored: {twitch_channel_ref.name}')
        
        # Start the message processor task
        self._message_processor_task = asyncio.create_task(self._process_message_queue())
        print('Message queue processor started')
        if last_signup_activity_at is None:
            mark_signup_activity(time.monotonic())
        self._signup_reminder_task = asyncio.create_task(self._process_signup_reminders())
        print('Signup reminder processor started')

        await send_welcome_message()

    async def _process_signup_reminders(self):
        """Background task that prompts chat when signups are idle."""
        while True:
            try:
                sleep_seconds = max(1.0, signup_reminder_interval_seconds)
                await asyncio.sleep(sleep_seconds)
                await send_signup_reminder_if_idle(time.monotonic())
            except asyncio.CancelledError:
                print("Signup reminder processor cancelled")
                break
            except Exception as e:
                print(f"Error in signup reminder processor: {e}")
                await asyncio.sleep(1)

    async def _process_message_queue(self):
        """Background task that processes queued messages respecting Twitch rate limits."""
        from twitchio.errors import IRCCooldownError
        
        global twitch_message_queue
        
        while True:
            try:
                # Wait for a message in the queue
                if twitch_message_queue is None:
                    await asyncio.sleep(0.1)
                    continue
                    
                message = await twitch_message_queue.get()
                
                if twitch_channel_ref is None:
                    # Channel not ready yet, wait a bit and put message back
                    await asyncio.sleep(0.5)
                    await twitch_message_queue.put(message)
                    continue
                
                # Try to send the message
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        await twitch_channel_ref.send(message)
                        # Success! Wait for rate limit before processing next message
                        await asyncio.sleep(MESSAGE_RATE_LIMIT)
                        break
                    except IRCCooldownError as e:
                        retry_count += 1
                        # Extract cooldown time from error message if possible
                        error_msg = str(e)
                        cooldown_match = re.search(r'(\d+\.?\d*)s', error_msg)
                        
                        if cooldown_match:
                            cooldown_time = float(cooldown_match.group(1))
                            print(f"Rate limit hit. Waiting {cooldown_time}s before retry {retry_count}/{max_retries}")
                            await asyncio.sleep(cooldown_time + 0.5)  # Add small buffer
                        else:
                            # Default wait time if we can't parse the error
                            wait_time = MESSAGE_RATE_LIMIT * (retry_count + 1)
                            print(f"Rate limit hit. Waiting {wait_time}s before retry {retry_count}/{max_retries}")
                            await asyncio.sleep(wait_time)
                        
                        if retry_count >= max_retries:
                            print(f"Failed to send message after {max_retries} retries: {message}")
                            break
                    except Exception as e:
                        print(f"Error sending message to Twitch: {e}")
                        # Wait a bit before trying next message
                        await asyncio.sleep(MESSAGE_RATE_LIMIT)
                        break
                
                # Mark task as done
                twitch_message_queue.task_done()
                
            except asyncio.CancelledError:
                print("Message queue processor cancelled")
                break
            except Exception as e:
                print(f"Error in message queue processor: {e}")
                await asyncio.sleep(1)

    # Events don't need decorators when subclassing
    async def event_message(self, message):
        # Make sure there is a message author. And make sure it isn't the bot
        if message.author is not None and message.author.name.lower() != BOT_NAME.lower() :
            message_text = message.content
            message_author = message.author.display_name
            await handle_message(message_text, message_author, twitch_message=message)

# Restore the queue on restart (because we like nice things)
if os.path.exists(entry_file_abs):
    # Restore that shit
    print("We restored that entry list since we restarted")
    with open(entry_file_abs) as f:
        # Iterate over the lines in the file
        for line in f:
            # Remove the newline character from the end of the line
            line = line.strip()

            if line != "":
                # Add the line to the deque
                entry_queue.append(line)

load_registration_state()

def listen_to_twitch():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    bot = Bot()
    bot.run()

    loop.run_until_complete(bot.run)
    loop.run_forever() # this is missing
    loop.close()



async def listen_to_youtube():
    # Set the publishedAfter parameter to the current time
    published_after = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)

    # Set up the YouTube API Service
    youtube = build('youtube', 'v3', developerKey=api_key)

    # Get actual video id from Youtube API for a given Youtube video string
    request = youtube.videos().list(
        part="liveStreamingDetails",
        id=youtube_video_id
    )
    response = request.execute()

    active_live_chat_id=""
    if "items" in response:
        video = response["items"][0]
        liveStreamingDetails = video["liveStreamingDetails"]
        active_live_chat_id = liveStreamingDetails.get("activeLiveChatId", "")
    else:
        print("There was an issue getting the live chat ID")

    # Start listening for messages since we have the actual chat ID the API needs
    if active_live_chat_id == "":
        return

    print("Active chat ID: " + active_live_chat_id)

    request = youtube.liveChatMessages().list(
        liveChatId=active_live_chat_id,
        part="snippet,authorDetails",
        pageToken="", #Start with an empty page token to get the first page of results
    )
    
    # Poll the response and retrieve new messages
    while True:
        print("Executing a response...")
        response = request.execute()

        # Print out the live chat messages
        if "items" in response:
            for message in response["items"]:
                message_time = parse(message['snippet']['publishedAt'])
                if (published_after > message_time):
                    continue
                snippet = message["snippet"]
                text = snippet["textMessageDetails"]["messageText"]
                author_details = message["authorDetails"]
                display_name = author_details["displayName"]
                print(f"{display_name}: {text}")
                await handle_message(text,display_name, youtube_message=message)

        # Check if there are more pages of results
        if "nextPageToken" in response:
            # Set the page token for the next request
            request = youtube.liveChatMessages().list(
                liveChatId=active_live_chat_id,
                part="snippet,authorDetails",
                pageToken=response["nextPageToken"],
            )
        else:
            # No more pages of results, exit the loop
            break

        # Give youtube a break. It hates being pounded
        await asyncio.sleep(30)

def obj_dict(obj):
    return obj.__dict__

def entries_json():
    # data to be saved to the CSV file
        data = []
        count = 1

        # Loop through entries
        for element in entry_queue:
            number = display_car_number(count)
            name = element

            # Add to data list
            data.append({'number': number, 'name': name})
            count += 1

        # Generate the json string
        json_string = json.dumps(data, default=obj_dict)
        return json_string

async def socket_comms(websocket, path):
    # LOOP THE RESPONSES so we keep it open
    async for msg in websocket:
        socket_data = "{}"
        if msg == "send_queue":
            # Generate JSON response
            socket_data = entries_json()
        elif msg == "latest_winner":
            socket_data = json.dumps(latest_winner_json(), default=obj_dict)
        
        try:
            await websocket.send(socket_data)
        except websockets.exceptions.ConnectionClosedError:
            print("Web Socket connection closed")

def setup_websocket():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # connect to the WebSocket server
    ws_server = websockets.serve(socket_comms, host=None, port=64209)

    loop.run_until_complete(ws_server)
    loop.run_forever() # this is missing
    loop.close()

def main():
    ws_server_thread = threading.Thread(target=setup_websocket, daemon=True)
    ws_server_thread.start()

    twitch_thread = threading.Thread(target=listen_to_twitch, daemon=True)
    twitch_thread.start()

    # asyncio.run(listen_to_youtube())

    twitch_thread.join()


if __name__ == "__main__":
    main()
