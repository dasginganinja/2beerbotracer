from dotenv import load_dotenv
import os
import collections
import itertools
import threading

from twitchio.ext import commands
from twitchio.message import Message as TwitchMessage

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
live_chat_id = os.getenv('YOUTUBE_LIVE_CHAT_ID')

# Create a queue for storing the usernames
entry_queue = collections.deque()

# Set maximum number of entries
MAX_ENTRIES = 15

# Handle incoming chat messages (passed data from twitch or Youtube)
async def handle_message(message: str, author: str, twitch_message: TwitchMessage = None):
    # Check if we have a race entry
    # !race !enter !join - add to queue
    # !startrace - remove the first MAX_ENTRIES from queue
    # !clearentries - clear list of entries
    # !entries - print entries in race

    is_mod = False
    if twitch_message is not None and twitch_message.author is not None:
        is_mod = twitch_message.author.is_mod

    if message.lower().startswith("!race") or message.lower().startswith("!enter") or message.lower().startswith("!join"):
        if author in entry_queue:
            await print_everywhere("You have already entered, " + author + ". Nice try :)", twitch_message=twitch_message)
            return

        # Add to entry queue
        entry_queue.append(author)

        # Print message when queue is full
        if len(entry_queue) >= MAX_ENTRIES:
            await print_everywhere("The list is full. Races starting soon!", twitch_message=twitch_message)
        else:
            await print_everywhere("You have been added, " + author, twitch_message=twitch_message)
    elif message.lower().startswith("!startrace") and is_mod:
        await print_everywhere("Starting race for " + ", ".join(itertools.islice(entry_queue,0,15)), twitch_message=twitch_message)
        # Remove the first MAX_ENTRIES from the queue
        for i in range(MAX_ENTRIES):
            if len(entry_queue) > 0:
                racer = entry_queue.popleft()
                
    elif message.lower().startswith("!clearentries") and is_mod:
        # Clear the queue
        entry_queue.clear()
        await print_everywhere("All entries have been cleared.", twitch_message=twitch_message)
    elif message.lower().startswith("!entries"):
        # Print the queue
        await print_everywhere("Race Entries: " + ", ".join(entry_queue), twitch_message=twitch_message)

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

# this will be called when the event READY is triggered, which will be on bot start

class Bot(commands.Bot):

    def __init__(self):
        super().__init__(token=access_token, client_id=client_id, nick=BOT_NAME, prefix='!', initial_channels=[TWITCH_CHANNEL])

    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

        await self.connected_channels[0].send("2BeerBot has connected and is ready for NATMAR. Available commands: !race !entries. Mod commands: !startrace !clearentries")

    # Events don't need decorators when subclassing
    async def event_message(self, message):
        # Make sure there is a message author. And make sure it isn't the bot
        if message.author is not None and message.author.name.lower() != BOT_NAME.lower() :
            message_text = message.content
            message_author = message.author.name
            await handle_message(message_text, message_author, twitch_message=message)

bot = Bot()
bot.run()

# do_test()