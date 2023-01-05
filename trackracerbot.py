from dotenv import load_dotenv
import os
import collections
import threading

from twitchAPI import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.types import AuthScope, ChatEvent
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, JoinedEvent
import asyncio

# Load the values from the .env file
load_dotenv()

# Use the values in the app
client_id = os.getenv('TWITCH_CLIENT_ID')
client_secret = os.getenv('TWITCH_CLIENT_SECRET')
api_key = os.getenv('YOUTUBE_API_KEY')
live_chat_id = os.getenv('YOUTUBE_LIVE_CHAT_ID')

# Create a queue for storing the usernames
entry_queue = collections.deque()

# Set maximum number of entries
MAX_ENTRIES = 15

# Set Twitch Channel to watch chat for
TWITCH_CHANNEL="2BeerMinimumRacing"

# Set scope for chat
USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

# Handle incoming chat messages (passed data from twitch or Youtube)
def handle_message(message, author):
    # Check if we have a race entry
    # !race !enter !join - add to queue
    # !startrace - remove the first MAX_ENTRIES from queue
    # !clearentries - clear list of entries
    # !entries - print entries in race

    if message.startswith("!race") or message.startswith("!enter") or message.startswith("!join"):
        if author in entry_queue:
            print_everywhere("You have already entered, " + author + ". Nice try :)")
            return

        # Add to entry queue
        entry_queue.append(author)

        # Print message when queue is full
        if len(entry_queue) >= MAX_ENTRIES:
            print_everywhere("The list is full. Races starting soon!")
        else:
            print_everywhere("You have been added, " + author)
    elif message.startswith("!startrace"):
        print_everywhere("Starting race and removing first " + str(MAX_ENTRIES) + " entries from the entry list.")
        # Remove the first MAX_ENTRIES from the queue
        for i in range(MAX_ENTRIES):
            if len(entry_queue) > 0:
                entry_queue.popleft()
    elif message.startswith("!clearentries"):
        # Clear the queue
        entry_queue.clear()
    elif message.startswith("!entries"):
        # Print the queue
        print_everywhere(", ".join(entry_queue))
    else:
        print("I farted")

# Function for printing the message in console, twitch, and youtube chats
def print_everywhere(logmessage):
    # Print to local console
    print(logmessage)

    # TODO: Print this message in Twitch chat
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
async def on_ready(ready_event: EventData):
    print('Bot is ready for work, joining channels')
    # join our target channel, if you want to join multiple, either call join for each individually
    # or even better pass a list of channels as the argument
    await ready_event.chat.join_room("2beerMinimumRacing")
    # you can do other bot initialization things in here


# this will be called whenever a message in a channel was send by either the bot OR another user
async def on_message(msg: ChatMessage):
    print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')
    # Pass this off to our handler to do queueing
    # handle_message(msg.text, msg.user.name)

async def on_joined(joined_event: JoinedEvent):
    print("This MF joined up in some channels!")
    print("This MF is in " + joined_event.room_name + " and my name is " + joined_event.user_name)
    
    await joined_event.chat.send_message(joined_event.room_name, "Locski deeeez nuts")


# this will be called whenever someone subscribes to a channel
async def on_sub(sub: ChatSub):
    print(f'New subscription in {sub.room.name}:\\n'
          f'  Type: {sub.sub_plan}\\n'
          f'  Message: {sub.sub_message}')


# this is where we set up the bot
async def listen_to_twitch():
    # set up twitch api instance and add user authentication with some scopes
    twitch = await Twitch(client_id, client_secret)
    auth = UserAuthenticator(twitch, USER_SCOPE)
    token, refresh_token = await auth.authenticate()
    await twitch.set_user_authentication(token, USER_SCOPE, refresh_token)

    # create chat instance
    chat = await Chat(twitch)

    # register the handlers for the events you want

    # listen to when the bot is done starting up and ready to join channels
    chat.register_event(ChatEvent.READY, on_ready)
    # listen for our bot joining a chat
    chat.register_event(ChatEvent.JOINED, on_joined)
    # listen to chat messages
    chat.register_event(ChatEvent.MESSAGE, on_message)

    # we are done with our setup, lets start this bot up!
    chat.start()

    # lets run till we press enter in the console
    try:
        input('press ENTER to stop\n')
    finally:
        # now we can close the chat bot and the twitch api client
        chat.stop()
        await twitch.close()


asyncio.run(listen_to_twitch())

# do_test()