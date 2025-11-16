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
    if str(user_id) not in STATS["user_activity"]:
        STATS["user_activity"][str(user_id)] = {"first_seen": datetime.now().isoformat(), "total_requests": 0}
    STATS["user_activity"][str(user_id)]["total_requests"] += 1
    STATS["user_activity"][str(user_id)]["last_seen"] = datetime.now().isoformat()
    save_stats(STATS)

def track_video_view(video_id):
    if video_id not in STATS["video_views"]:
        STATS["video_views"][video_id] = 0
    STATS["video_views"][video_id] += 1
    save_stats(STATS)

# --------------------------
# Telegram Bot Functions
# --------------------------
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False
    return True

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    track_user(user_id)
    
    if context.args:
        video_id = context.args[0]
        is_member = await check_membership(user_id, context)
        
        if not is_member:
            keyboard = [[InlineKeyboardButton(f"✅ Join {c['name']}", url=f"https://t.me/{c['username'][1:]}")] for c in REQUIRED_CHANNELS]
            keyboard.append([InlineKeyboardButton("✔️ Check Again", callback_data="check_membership")])
            await update.message.reply_text("🔒 Join channels first!", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
            context.user_data['pending_video'] = video_id
            return
        
        if video_id in VIDEOS:
            track_video_view(video_id)
            await update.message.reply_video(VIDEOS[video_id], caption=f"✅ Enjoy! 🔔 {CONTENT_CHANNEL}", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("❌ Invalid video ID!")
        return

    # Normal welcome
    await update.message.reply_text(f"✅ Access Granted!\nClick your video link.\n/help for commands", parse_mode=ParseMode.HTML)

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS:
        text = "👑 Admin commands:\n/addvideo /videos /delvideo /stats /broadcast /topvideos"
    else:
        text = "ℹ️ User commands:\n/start /help /about /myactivity"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# About command
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🤖 Bot Info\nUsers: {len(STATS['total_users'])}\nVideos: {len(VIDEOS)}", parse_mode=ParseMode.HTML)

# My Activity
async def my_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    activity = STATS["user_activity"].get(user_id)
    if activity:
        await update.message.reply_text(f"📊 Your Activity\nRequests: {activity['total_requests']}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ No data!")

# Button Callback
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check_membership":
        if await check_membership(query.from_user.id, context):
            await query.edit_message_text(f"✅ Verified!\n📢 {CONTENT_CHANNEL}", parse_mode=ParseMode.HTML)
            if 'pending_video' in context.user_data:
                vid = context.user_data['pending_video']
                if vid in VIDEOS:
                    track_video_view(vid)
                    await query.message.reply_video(VIDEOS[vid])
                del context.user_data['pending_video']
        else:
            await query.answer("❌ Join channels first!", show_alert=True)

# Admin commands: add/list/delete/stats/top/broadcast
async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not update.message.video or not context.args:
        await update.message.reply_text("Send video with /addvideo video_id")
        return
    vid = context.args[0]
    VIDEOS[vid] = update.message.video.file_id
    save_videos(VIDEOS)
    bot_username = (await context.bot.get_me()).username
    await update.message.reply_text(f"✅ Added!\nLink: https://t.me/{bot_username}?start={vid}")

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not VIDEOS: await update.message.reply_text("No videos!"); return
    await update.message.reply_text("\n".join(VIDEOS.keys()))

async def delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args: return
    vid = context.args[0]
    if vid in VIDEOS: del VIDEOS[vid]; save_videos(VIDEOS); await update.message.reply_text(f"Deleted: {vid}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    total_views = sum(STATS["video_views"].values())
    await update.message.reply_text(f"Users: {len(STATS['total_users'])}\nVideos: {len(VIDEOS)}\nViews: {total_views}")

async def top_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    top = sorted(STATS["video_views"].items(), key=lambda x: x[1], reverse=True)[:10]
    await update.message.reply_text("\n".join([f"{i+1}. {v} - {c} views" for i, (v, c) in enumerate(top)]))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if not context.args: return
    msg = " ".join(context.args)
    count = 0
    for user in STATS["total_users"]:
        try: await context.bot.send_message(user, msg); count+=1
        except: pass
    await update.message.reply_text(f"Sent to {count} users!")

# --------------------------
# Flask Webhook Route
# --------------------------
application = Application.builder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("about", about_command))
application.add_handler(CommandHandler("myactivity", my_activity))
application.add_handler(CommandHandler("addvideo", add_video))
application.add_handler(CommandHandler("videos", list_videos))
application.add_handler(CommandHandler("delvideo", delete_video))
application.add_handler(CommandHandler("stats", stats_command))
application.add_handler(CommandHandler("topvideos", top_videos))
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(CallbackQueryHandler(button_callback))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

# --------------------------
# Run Flask App
# --------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
