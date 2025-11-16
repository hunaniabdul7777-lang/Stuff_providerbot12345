import logging
import json
import os
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA"
REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "@stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "@stuffprovider_proofs", "id": -1001963037939}
]
CONTENT_CHANNEL = "@stuffprovider_demo"
ADMIN_IDS = [5967565554]

DB_FILE = "videos_db.json"
STATS_FILE = "stats_db.json"

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
                return json.load(f)
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
if isinstance(STATS.get("total_users"), list):
    STATS["total_users"] = set(STATS["total_users"])

logger.info(f"Loaded {len(VIDEOS)} videos from database")

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

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            logger.error(f"Error: {e}")
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
            keyboard = []
            for channel in REQUIRED_CHANNELS:
                keyboard.append([InlineKeyboardButton(f"✅ Join {channel['name']}", url=f"https://t.me/{channel['username'][1:]}")])
            keyboard.append([InlineKeyboardButton("✔️ Check Again", callback_data="check_membership")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🔒 <b>Access Denied!</b>\n\nPehle channels join karo, phir 'Check Again' dabao!",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            context.user_data['pending_video'] = video_id
            return
        
        if video_id in VIDEOS:
            try:
                track_video_view(video_id)
                await update.message.reply_video(
                    video=VIDEOS[video_id],
                    caption=f"✅ <b>Enjoy!</b>\n\n🔔 {CONTENT_CHANNEL}",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")
        else:
            await update.message.reply_text("❌ Invalid link!")
    else:
        is_member = await check_membership(user_id, context)
        
        if not is_member:
            keyboard = []
            for channel in REQUIRED_CHANNELS:
                keyboard.append([InlineKeyboardButton(f"✅ Join {channel['name']}", url=f"https://t.me/{channel['username'][1:]}")])
            keyboard.append([InlineKeyboardButton("✔️ Check Again", callback_data="check_membership")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"👋 <b>Welcome {user.first_name}!</b>\n\n🔒 Channels join karo:\n\n1️⃣ {REQUIRED_CHANNELS[0]['username']}\n2️⃣ {REQUIRED_CHANNELS[1]['username']}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                f"✅ <b>Access Granted!</b>\n\n📢 {CONTENT_CHANNEL} se links click karo!\n\n💡 /help for commands",
                parse_mode=ParseMode.HTML
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in ADMIN_IDS:
        help_text = "👑 <b>Admin:</b>\n/addvideo /videos /delvideo /stats /broadcast /topvideos"
    else:
        help_text = "ℹ️ <b>Commands:</b>\n/start /help /about /myactivity"
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 <b>Bot Info</b>\n\n👥 Users: {len(STATS['total_users'])}\n🎥 Videos: {len(VIDEOS)}",
        parse_mode=ParseMode.HTML
    )

async def my_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in STATS["user_activity"]:
        activity = STATS["user_activity"][user_id]
        await update.message.reply_text(
            f"📊 <b>Your Activity</b>\n\n📈 Requests: {activity['total_requests']}",
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
            await query.edit_message_text(
                f"✅ <b>Verified!</b>\n\n📢 {CONTENT_CHANNEL} se links click karo!",
                parse_mode=ParseMode.HTML
            )
            
            if 'pending_video' in context.user_data:
                video_id = context.user_data['pending_video']
                if video_id in VIDEOS:
                    track_video_view(video_id)
                    await query.message.reply_video(
                        video=VIDEOS[video_id],
                        caption=f"✅ Video!",
                        parse_mode=ParseMode.HTML
                    )
                del context.user_data['pending_video']
        else:
            await query.answer("❌ Channels join nahi kiye!", show_alert=True)

async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not update.message.video:
        await update.message.reply_text("📹 Send video with: /addvideo video_id")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Missing ID!")
        return
    
    video_id = context.args[0]
    file_id = update.message.video.file_id
    
    VIDEOS[video_id] = file_id
    save_videos(VIDEOS)
    
    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={video_id}"
    
    await update.message.reply_text(
        f"✅ Added!\n\n🔗 <code>{share_link}</code>\n\n📊 Total: {len(VIDEOS)}",
        parse_mode=ParseMode.HTML
    )

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not VIDEOS:
        await update.message.reply_text("❌ No videos!")
        return
    
    video_list = "\n".join([f"• <code>{v}</code>" for v in list(VIDEOS.keys())[:20]])
    await update.message.reply_text(f"📹 <b>Videos ({len(VIDEOS)}):</b>\n\n{video_list}", parse_mode=ParseMode.HTML)

async def delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /delvideo video_id")
        return
    
    video_id = context.args[0]
    
    if video_id in VIDEOS:
        del VIDEOS[video_id]
        save_videos(VIDEOS)
        await update.message.reply_text(f"✅ Deleted! Remaining: {len(VIDEOS)}")
    else:
        await update.message.reply_text("❌ Not found!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    total_views = sum(STATS["video_views"].values())
    await update.message.reply_text(
        f"📊 <b>Stats</b>\n\n👥 Users: {len(STATS['total_users'])}\n🎥 Videos: {len(VIDEOS)}\n👁 Views: {total_views}",
        parse_mode=ParseMode.HTML
    )

async def top_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not STATS["video_views"]:
        await update.message.reply_text("❌ No views!")
        return
    
    sorted_videos = sorted(STATS["video_views"].items(), key=lambda x: x[1], reverse=True)[:10]
    top_list = "\n".join([f"{i}. <code>{v}</code> - {c} views" for i, (v, c) in enumerate(sorted_videos, 1)])
    
    await update.message.reply_text(f"🏆 <b>Top Videos:</b>\n\n{top_list}", parse_mode=ParseMode.HTML)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast message")
        return
    
    message = " ".join(context.args)
    success = 0
    
    for user_id in STATS["total_users"]:
        try:
            await context.bot.send_message(user_id, f"📢 {message}")
            success += 1
        except:
            pass
    
    await update.message.reply_text(f"✅ Sent to {success} users!")

def main():
    def run_flask():
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)
    
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
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
    
    logger.info("🚀 Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
