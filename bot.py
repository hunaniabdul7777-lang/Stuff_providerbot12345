import logging
import json
import os
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# --------------------------
# Bot Configuration (same as yours)
# --------------------------
BOT_TOKEN = "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA"

REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "@stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "@stuffprovider_proofs", "id": -1001963037939}
]

CONTENT_CHANNEL = "@stuffprovider_demo"
ADMIN_IDS = [5967565554]

DB_FILE = "videos_db.json"
STATS_FILE = "stats_db.json"

# --------------------------
# Flask App
# --------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

# --------------------------
# Logging
# --------------------------
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------
# Load/Save DB
# --------------------------
def load_videos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_videos(videos):
    with open(DB_FILE, 'w') as f:
        json.dump(videos, f, indent=2)

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data.get("total_users"), list):
                    data["total_users"] = set(data["total_users"])
                return data
        except:
            return {"total_users": set(), "video_views": {}, "user_activity": {}}
    return {"total_users": set(), "video_views": {}, "user_activity": {}}

def save_stats(stats):
    stats_copy = stats.copy()
    stats_copy["total_users"] = list(stats["total_users"])
    with open(STATS_FILE, 'w') as f:
        json.dump(stats_copy, f, indent=2)

VIDEOS = load_videos()
STATS = load_stats()
logger.info(f"Loaded {len(VIDEOS)} videos from database")

# --------------------------
# Tracking Functions
# --------------------------
def track_user(user_id):
    STATS["total_users"].add(user_id)
    if str(user_id) not
