from dotenv import load_dotenv
import os
import collections
import itertools
# import threading
import asyncio

from twitchio.ext import commands
from twitchio.message import Message as TwitchMessage

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
import datetime
import google
from dateutil.parser import parse
import pytz

# Load the values from the .env file
load_dotenv()

# Use the values in the app
client_id = os.getenv('TWITCH_CLIENT_ID')
client_secret = os.getenv('TWITCH_CLIENT_SECRET')
access_token = os.getenv('TWITCH_ACCESS_TOKEN')
refresh_token = os.getenv('TWITCH_REFRESH_TOKEN')
TWITCH_CHANNEL = os.getenv('TWITCH_CHANNEL')
BOT_NAME = os.getenv('TWITCH_BOT_NAME')
api_key = os.getenv('YOUTUBE_API_KEY')
youtube_video_id = os.getenv('YOUTUBE_LIVE_VIDEO_ID')
entry_file = os.getenv('ENTRY_FILE')

# Create a queue for storing the usernames
entry_queue = collections.deque()

# Variable for absolute path to Entry File
entry_file_abs = ""
if entry_file is None:
    entry_file = "entries.txt"

# Set the absolute path to the savefile
entry_file_abs = os.path.abspath(entry_file)

# Set maximum number of entries
MAX_ENTRIES = 30

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

    is_mod = False
    if twitch_message is not None and twitch_message.author is not None:
        is_mod = twitch_message.author.is_mod

    if message.lower().startswith("!commands"):
        commands_message = "Available commands: !play !entries"
        if is_mod:
            commands_message += " // Mod Commands: !start !clearentries"
        await print_everywhere(commands_message, twitch_message=twitch_message)

    if message.lower().startswith("!race") or message.lower().startswith("!play") or message.lower().startswith("!enter") or message.lower().startswith("!join") or message.count("artmannJudy") or message.count("x100pr3Mychair") or message.count("x2beerShrek") or message.count("avoidr3Hotdogman") or message.count("spacec122GoodVibes") or message.count("artmannNatmar"):
        if author in entry_queue:
            await print_everywhere("You have already entered " + author + ". Nice try :)", twitch_message=twitch_message)
            return

        # Add to queue, or print full message
        if len(entry_queue) < MAX_ENTRIES:
            # Add to entry queue
            entry_queue.append(author)

            # Write to a file for the MAX_ENTRIES
            bang_out_queue_to_file(entry_file_abs)
            

            await print_everywhere("You have been added " + author, twitch_message=twitch_message)
        else:
            await print_everywhere("The list is full. Better luck next race!", twitch_message=twitch_message)

    elif message.lower().startswith("!start") and is_mod:
        await print_everywhere("Starting for " + ", ".join(itertools.islice(entry_queue,0,MAX_ENTRIES)), twitch_message=twitch_message)
        # Clear the queue
        clear_queue()
                
    elif message.lower().startswith("!clearentries") and is_mod:
        # Clear the queue
        clear_queue()
        await print_everywhere("All entries have been cleared.", twitch_message=twitch_message)

    elif message.lower().startswith("!entries"):
        # Print the queue
        await print_everywhere("Race Entries: " + ", ".join(entry_queue), twitch_message=twitch_message)

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

    # TODO: Print this message in Twitch chat
    if twitch_message is not None:
        await twitch_message.channel.send(logmessage)

    # TODO: Print this message in YT chat

# Testing of the handle message function is essential to make sure this works as expected.
def do_test():
    # Testing Inputs to simulate chat
    handle_message("hello fuck boiii", "2beer")

    # Test Entries
    handle_message("!race", "2beer")
    handle_message("!race", "AvoidRalph")
    handle_message("!race", "2beer")
    handle_message("!race", "AvoidRalph")
    handle_message("!join", "ArtMann")
    handle_message("!join", "RubbingIsRacing")
    handle_message("!enter", "SuperBee2315")
    handle_message("!entries", "2beer")
    handle_message("!startrace", "ArtMann")

    # Simulate 2nd race
    handle_message("!race", "2beer")
    for i in range(MAX_ENTRIES):
        handle_message("!join", "testracer" + str(i))
    handle_message("!entries", "ArtMann")
    handle_message("!startrace", "ArtMann")

    # There should be one entry left
    handle_message("!entries", "ArtMann")

class Bot(commands.Bot):

    def __init__(self):
        super().__init__(token=access_token, client_id=client_id, nick=BOT_NAME, prefix='!', initial_channels=[TWITCH_CHANNEL])

    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

        await self.connected_channels[0].send("2BeerBot has connected and is ready for NATMAR. !commands for more info")

    # Events don't need decorators when subclassing
    async def event_message(self, message):
        # Make sure there is a message author. And make sure it isn't the bot
        if message.author is not None and message.author.name.lower() != BOT_NAME.lower() :
            message_text = message.content
            message_author = message.author.name
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

def listen_to_twitch():
    bot = Bot()
    bot.run()


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
        # print("Executing a response...")
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
        time.sleep(15)

def test_writing_to_youtube():
    youtube = build('youtube', 'v3', developerKey=api_key)
    active_live_chat_id = "Cg0KC2UtVXMwalBWTVVZKicKGFVDRU5BZGE1WlJla2docjlqM0dFX3Z1dxILZS1VczBqUFZNVVk"
    request = youtube.liveChatMessages().insert(
        part="snippet",
        body={
            "snippet": {
                "liveChatId": active_live_chat_id,
                "type": "textMessageEvent",
                "textMessageDetails": {
                    "messageText": "Hello, world!"
                }
            }
        }
    )
    response = request.execute()

    # Print the response
    print(response)


# do_test()
# asyncio.run(listen_to_youtube())
asyncio.run(listen_to_twitch())