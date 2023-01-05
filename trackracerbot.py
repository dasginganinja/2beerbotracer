from dotenv import load_dotenv
import os
import collections
import threading

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

# Function to listen to Twitch chat
def listen_to_twitch():
    # Code to connect twitch chat
    

    while True:
        # Get the next message from chat
        message = get_next_message()

        # Handle the message
        handle_message(message.message, message.author)

# Function to listen to Youtube Live Chat
def listen_to_youtube_live():
    # Code to connect Youtube chat

    while True:
        # Get the next message from chat
        message = get_next_message()

        # Handle the message
        handle_message(message.message, message.author)


# Create the chat listening threads
thread_twitch = threading.Thread(target=listen_to_twitch)
# thread_youtube = threading.Thread(target=listen_to_youtube_live)

# Start chat listening threads
thread_twitch.start()
# thread_youtube.start()