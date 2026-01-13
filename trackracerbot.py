from dotenv import load_dotenv
import os
import collections
import itertools
import threading
import asyncio

from twitchio.ext import commands
from twitchio.message import Message as TwitchMessage

from googleapiclient.discovery import build
import datetime
from dateutil.parser import parse
import pytz

import websockets
import json
import re

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

# Message queue for Twitch chat to handle rate limiting
# Will be initialized when Bot is ready (needs event loop)
twitch_message_queue = None
twitch_channel_ref = None  # Will be set when bot is ready

# Rate limiting: Twitch allows ~20 messages per 30 seconds for regular users
# We'll be conservative and send 1 message per 1.5 seconds (20 per 30s)
MESSAGE_RATE_LIMIT = 1.5  # seconds between messages

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
    if youtube_message is not None and youtube_message["authorDetails"] is not None:
        is_mod = youtube_message['authorDetails']['isChatOwner'] or youtube_message['authorDetails']['isChatModerator']

    if message.lower().startswith("!commands"):
        commands_message = "Available commands: !play !entries"
        if is_mod:
            commands_message += " // Mod Commands: !start !clearentries"
        await print_everywhere(commands_message, twitch_message=twitch_message)

    if message.lower().startswith("!race") or message.lower().startswith("!play") or message.lower().startswith("!enter") or message.lower().startswith("!join") or message.count("artmannJudy") or message.count("x100pr3Hndoclap52") or message.count("x2beerShrek") or message.count("avoidr3Hotdogman") or message.count("spacec122GoodVibes") or message.count("artmannNatmar") or message.count("artmannOhyeah"):
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

        # await self.connected_channels[0].send("2BeerBot has connected and is ready for NATMAR. !commands for more info")

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
            number = count
            # Custom number for 29 per Art's request
            if number == 29:
                number = 69
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
            global latest_winner
            socket_data = latest_winner
        
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

ws_server_thread = threading.Thread(target=setup_websocket, daemon=True)
ws_server_thread.start()

twitch_thread = threading.Thread(target=listen_to_twitch, daemon=True)
twitch_thread.start()

# asyncio.run(listen_to_youtube())

twitch_thread.join()
