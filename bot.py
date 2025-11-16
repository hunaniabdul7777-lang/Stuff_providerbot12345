import logging
import json
import os
from datetime import datetime
from threading import Thread
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from telegram.constants import ParseMode

# -----------------------------
# CONFIGURATION (CHANGE AS NEEDED)
# -----------------------------
BOT_TOKEN = "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA"
REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "@stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "@stuffprovider_proofs", "id": -1001963037939}
]
CONTENT_CHANNEL = "@stuffprovider_demo"
ADMIN_IDS = [5967565554]

DB_FILE = "videos_db.json"
STATS_FILE = "stats_db.json"

# -----------------------------
# FLASK APP (Webhook server)
# -----------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

# -----------------------------
# LOGGING
# -----------------------------
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# DATABASE FUNCTIONS
# -----------------------------
def load_videos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_videos(videos):
    with open(DB_FILE, 'w') as f:
        json.dump(videos, f, indent=2)

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            try:
                data = json.load(f)
                data["total_users"] = set(data.get("total_users", []))
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

# -----------------------------
# TRACKING FUNCTIONS
# -----------------------------
def track_user(user_id):
    STATS["total_users"].add(user_id)
    uid = str(user_id)
    if uid not in STATS["user_activity"]:
        STATS["user_activity"][uid] = {"first_seen": datetime.now().isoformat(), "total_requests": 0}
    STATS["user_activity"][uid]["total_requests"] += 1
    STATS["user_activity"][uid]["last_seen"] = datetime.now().isoformat()
    save_stats(STATS)

def track_video_view(video_id):
    if video_id not in STATS["video_views"]:
        STATS["video_views"][video_id] = 0
    STATS["video_views"][video_id] += 1
    save_stats(STATS)

# -----------------------------
# BOT FUNCTIONS
# -----------------------------
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            logger.error(f"Membership check error: {e}")
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    track_user(user_id)

    if context.args:
        video_id = context.args[0]
        is_member = await check_membership(user_id, context)
        if not is_member:
            keyboard = [
                [InlineKeyboardButton(f"✅ Join {c['name']}", url=f"https://t.me/{c['username'][1:]}")] 
                for c in REQUIRED_CHANNELS
            ]
            keyboard.append([InlineKeyboardButton("✔️ Check Again", callback_data="check_membership")])
            await update.message.reply_text(
                "🔒 <b>Access Denied!</b>\n\nPehle channels join karo, phir 'Check Again' dabao!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            context.user_data['pending_video'] = video_id
            return
        
        if video_id in VIDEOS:
            track_video_view(video_id)
            await update.message.reply_video(
                video=VIDEOS[video_id],
                caption=f"✅ Enjoy!\n🔔 {CONTENT_CHANNEL}",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ Invalid link!")
    else:
        is_member = await check_membership(user_id, context)
        if not is_member:
            keyboard = [
                [InlineKeyboardButton(f"✅ Join {c['name']}", url=f"https://t.me/{c['username'][1:]}")] 
                for c in REQUIRED_CHANNELS
            ]
            keyboard.append([InlineKeyboardButton("✔️ Check Again", callback_data="check_membership")])
            await update.message.reply_text(
                f"👋 <b>Welcome {user.first_name}!</b>\n\n🔒 Channels join karo:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                f"✅ <b>Access Granted!</b>\n📢 {CONTENT_CHANNEL} se links click karo!\n💡 /help",
                parse_mode=ParseMode.HTML
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS:
        help_text = "👑 Admin:\n/addvideo /delvideo /videos /stats /broadcast /topvideos"
    else:
        help_text = "ℹ️ User:\n/start /help /about /myactivity"
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 Bot Info\n👥 Users: {len(STATS['total_users'])}\n🎥 Videos: {len(VIDEOS)}",
        parse_mode=ParseMode.HTML
    )

async def my_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    activity = STATS["user_activity"].get(uid)
    if activity:
        await update.message.reply_text(
            f"📊 Your Activity\nRequests: {activity['total_requests']}",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("❌ No data!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "check_membership":
        is_member = await check_membership(user_id, context)
        if is_member:
            await query.edit_message_text(f"✅ Verified!\n📢 {CONTENT_CHANNEL} se links click karo!")
            if 'pending_video' in context.user_data:
                vid = context.user_data['pending_video']
                if vid in VIDEOS:
                    track_video_view(vid)
                    await query.message.reply_video(VIDEOS[vid], caption="✅ Video!")
                del context.user_data['pending_video']
        else:
            await query.answer("❌ Channels join nahi kiye!", show_alert=True)

# -----------------------------
# ADMIN COMMANDS
# -----------------------------
async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("❌ Unauthorized!")
    if not update.message.video:
        return await update.message.reply_text("📹 Send video with /addvideo video_id")
    if not context.args:
        return await update.message.reply_text("❌ Missing video ID!")
    
    vid_id = context.args[0]
    VIDEOS[vid_id] = update.message.video.file_id
    save_videos(VIDEOS)
    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={vid_id}"
    await update.message.reply_text(f"✅ Added!\nLink: {share_link}\nTotal videos: {len(VIDEOS)}")

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not VIDEOS:
        return await update.message.reply_text("❌ No videos!")
    text = "\n".join([f"• {v}" for v in VIDEOS.keys()])
    await update.message.reply_text(f"📹 Videos ({len(VIDEOS)}):\n{text}")

async def delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        return await update.message.reply_text("❌ Usage: /delvideo video_id")
    vid = context.args[0]
    if vid in VIDEOS:
        del VIDEOS[vid]
        save_videos(VIDEOS)
        await update.message.reply_text(f"✅ Deleted! Remaining: {len(VIDEOS)}")
    else:
        await update.message.reply_text("❌ Not found!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    total_views = sum(STATS["video_views"].values())
    await update.message.reply_text(
        f"📊 Stats\nUsers: {len(STATS['total_users'])}\nVideos: {len(VIDEOS)}\nViews: {total_views}"
    )

async def top_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not STATS["video_views"]:
        return await update.message.reply_text("❌ No views yet!")
    sorted_vids = sorted(STATS["video_views"].items(), key=lambda x: x[1], reverse=True)[:10]
    text = "\n".join([f"{i+1}. {v} - {c} views" for i, (v, c) in enumerate(sorted_vids)])
    await update.message.reply_text(f"🏆 Top Videos:\n{text}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        return await update.message.reply_text("Usage: /broadcast message")
    msg = " ".join(context.args)
    success = 0
    for user_id in STATS["total_users"]:
        try:
            await context.bot.send_message(user_id, f"📢 {msg}")
            success += 1
        except:
            continue
    await update.message.reply_text(f"✅ Sent to {success} users!")

# -----------------------------
# MAIN
# -----------------------------
def main():
    # Flask thread
    def run_flask():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)
    Thread(target=run_flask, daemon=True).start()

    # Telegram bot application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("myactivity", my_activity))
    
    application.add_handler(CommandHandler("addvideo", add_video))
    application.add_handler(CommandHandler("delvideo", delete_video))
    application.add_handler(CommandHandler("videos", list_videos))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("topvideos", top_videos))
    application.add_handler(CommandHandler("broadcast", broadcast))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🚀 Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
