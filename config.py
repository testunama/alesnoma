import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
PORT = int(os.getenv('PORT', 8080))

FREE_TIER_LIMIT = 3
PREMIUM_TIER_LIMIT = 20
FREE_MONITOR_DURATION = 5
PREMIUM_MONITOR_DURATION = 1
ALLOWED_SCHEMES = ['http://', 'https://']
TIMEOUT = 10
