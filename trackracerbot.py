from dotenv import load_dotenv

# Load the values from the .env file
load_dotenv()

# Use the values in the app
client_id = os.getenv('TWITCH_CLIENT_ID')
client_secret = os.getenv('TWITCH_CLIENT_SECRET')
api_key = os.getenv('YOUTUBE_API_KEY')
live_chat_id = os.getenv('YOUTUBE_LIVE_CHAT_ID')