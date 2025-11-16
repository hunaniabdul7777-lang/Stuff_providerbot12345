import logging
import json
import os
from datetime import datetime
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
                "🔒 <b>Access Denied!</b>\n\nPehle channels join karo, phir 'Check Again' dabao!\n\n⚠️ Dono channels zaroori hain!",
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
                    caption=f"✅ <b>Enjoy your video!</b>\n\n🔔 More content: {CONTENT_CHANNEL}\n👥 Join for latest updates!",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")
        else:
            await update.message.reply_text("❌ Invalid video link!")
    else:
        is_member = await check_membership(user_id, context)
        
        if not is_member:
            keyboard = []
            for channel in REQUIRED_CHANNELS:
                keyboard.append([InlineKeyboardButton(f"✅ Join {channel['name']}", url=f"https://t.me/{channel['username'][1:]}")])
            keyboard.append([InlineKeyboardButton("✔️ Check Again", callback_data="check_membership")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"👋 <b>Welcome {user.first_name}!</b>\n\n"
                f"🎬 Premium content ka access chahiye?\n\n"
                f"🔒 Pehle yeh channels join karo:\n\n"
                f"1️⃣ {REQUIRED_CHANNELS[0]['username']}\n"
                f"2️⃣ {REQUIRED_CHANNELS[1]['username']}\n\n"
                f"✅ Join karne ke baad 'Check Again' dabao!",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            keyboard = [
                [InlineKeyboardButton("📢 Content Channel", url=f"https://t.me/{CONTENT_CHANNEL[1:]}")],
                [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"✅ <b>Access Granted {user.first_name}!</b>\n\n"
                f"🎉 Aap ab bot use kar sakte ho!\n\n"
                f"📢 Latest videos ke liye {CONTENT_CHANNEL} join karo aur links click karo!\n\n"
                f"💡 Type /help for more commands",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in ADMIN_IDS:
        help_text = (
            "👑 <b>Admin Commands:</b>\n\n"
            "📹 <b>Video Management:</b>\n"
            "/addvideo - Add new video\n"
            "/videos - List all videos\n"
            "/delvideo - Delete video\n"
            "/search - Search videos\n\n"
            "📊 <b>Statistics:</b>\n"
            "/stats - Bot statistics\n"
            "/topvideos - Most viewed videos\n"
            "/users - Total users count\n\n"
            "📢 <b>Broadcasting:</b>\n"
            "/broadcast - Send message to all users\n\n"
            "👤 <b>User Commands:</b>\n"
            "/start - Start bot\n"
            "/help - Show this message\n"
            "/about - About bot\n"
            "/myactivity - Your activity"
        )
    else:
        help_text = (
            "ℹ️ <b>Available Commands:</b>\n\n"
            "/start - Start bot\n"
            "/help - Show this message\n"
            "/about - About this bot\n"
            "/myactivity - Your activity stats\n\n"
            "💡 <b>How to use:</b>\n"
            "1️⃣ Join required channels\n"
            "2️⃣ Go to content channel\n"
            "3️⃣ Click on video links\n"
            "4️⃣ Enjoy premium content!"
        )
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        "🤖 <b>About This Bot</b>\n\n"
        "📹 Premium content provider bot\n"
        "🔒 Secure channel verification\n"
        "⚡ Fast content delivery\n"
        "🎬 HD quality videos\n\n"
        f"📢 Channel: {CONTENT_CHANNEL}\n"
        f"👥 Total Users: {len(STATS['total_users'])}\n"
        f"🎥 Total Videos: {len(VIDEOS)}\n\n"
        "💡 Type /help for commands"
    )
    
    await update.message.reply_text(about_text, parse_mode=ParseMode.HTML)

async def my_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in STATS["user_activity"]:
        activity = STATS["user_activity"][user_id]
        first_seen = datetime.fromisoformat(activity["first_seen"]).strftime("%d %b %Y")
        last_seen = datetime.fromisoformat(activity["last_seen"]).strftime("%d %b %Y, %H:%M")
        
        activity_text = (
            f"📊 <b>Your Activity</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"📅 First Visit: {first_seen}\n"
            f"🕐 Last Visit: {last_seen}\n"
            f"📈 Total Requests: {activity['total_requests']}\n\n"
            f"Thank you for using our bot! 🎉"
        )
    else:
        activity_text = "❌ No activity data found!"
    
    await update.message.reply_text(activity_text, parse_mode=ParseMode.HTML)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "check_membership":
        is_member = await check_membership(user_id, context)
        
        if is_member:
            await query.edit_message_text(
                f"✅ <b>Verified!</b>\n\n"
                f"Aap ab bot use kar sakte ho!\n\n"
                f"📢 {CONTENT_CHANNEL} se links click karo!",
                parse_mode=ParseMode.HTML
            )
            
            if 'pending_video' in context.user_data:
                video_id = context.user_data['pending_video']
                if video_id in VIDEOS:
                    track_video_view(video_id)
                    await query.message.reply_video(
                        video=VIDEOS[video_id],
                        caption=f"✅ <b>Enjoy!</b>\n\n🔔 {CONTENT_CHANNEL}",
                        parse_mode=ParseMode.HTML
                    )
                del context.user_data['pending_video']
        else:
            await query.answer("❌ Channels join nahi kiye!", show_alert=True)
    
    elif query.data == "help":
        await help_command(update, context)

async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not update.message.video:
        await update.message.reply_text(
            "📹 <b>How to add video:</b>\n\n"
            "1. Video bhejo (50MB tak)\n"
            "2. Caption: /addvideo video_id\n\n"
            "Example: /addvideo movie_1\n\n"
            "💡 Tip: Use short, memorable IDs",
            parse_mode=ParseMode.HTML
        )
        return
    
    if not context.args:
        await update.message.reply_text("❌ Video ID missing!\nUsage: /addvideo video_id")
        return
    
    video_id = context.args[0]
    
    if video_id in VIDEOS:
        await update.message.reply_text(f"⚠️ Video ID <code>{video_id}</code> already exists!\nUse different ID.", parse_mode=ParseMode.HTML)
        return
    
    file_id = update.message.video.file_id
    
    VIDEOS[video_id] = file_id
    save_videos(VIDEOS)
    
    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={video_id}"
    
    await update.message.reply_text(
        f"✅ <b>Video Added Successfully!</b>\n\n"
        f"🆔 Video ID: <code>{video_id}</code>\n"
        f"🔗 Share Link:\n<code>{share_link}</code>\n\n"
        f"📊 Total Videos: {len(VIDEOS)}\n\n"
        f"📢 Ab is link ko {CONTENT_CHANNEL} mein share karo!",
        parse_mode=ParseMode.HTML
    )

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not VIDEOS:
        await update.message.reply_text("❌ No videos added yet!\nUse /addvideo to add videos.")
        return
    
    video_list = []
    for idx, vid_id in enumerate(VIDEOS.keys(), 1):
        views = STATS["video_views"].get(vid_id, 0)
        video_list.append(f"{idx}. <code>{vid_id}</code> - 👁 {views} views")
    
    videos_text = "\n".join(video_list)
    
    await update.message.reply_text(
        f"📹 <b>All Videos ({len(VIDEOS)}):</b>\n\n{videos_text}\n\n"
        f"💡 Use /search to find specific video",
        parse_mode=ParseMode.HTML
    )

async def search_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /search video_id")
        return
    
    search_term = context.args[0].lower()
    results = [vid_id for vid_id in VIDEOS.keys() if search_term in vid_id.lower()]
    
    if results:
        result_list = "\n".join([f"• <code>{vid}</code>" for vid in results])
        await update.message.reply_text(
            f"🔍 <b>Search Results ({len(results)}):</b>\n\n{result_list}",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("❌ No videos found!")

async def delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /delvideo video_id")
        return
    
    video_id = context.args[0]
    
    if video_id in VIDEOS:
        del VIDEOS[video_id]
        save_videos(VIDEOS)
        await update.message.reply_text(
            f"✅ Video <code>{video_id}</code> deleted successfully!\n\n"
            f"📊 Remaining: {len(VIDEOS)} videos",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("❌ Video not found!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    total_views = sum(STATS["video_views"].values())
    
    stats_text = (
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 Total Users: {len(STATS['total_users'])}\n"
        f"🎥 Total Videos: {len(VIDEOS)}\n"
        f"👁 Total Views: {total_views}\n"
        f"📈 Avg Views/Video: {total_views // len(VIDEOS) if VIDEOS else 0}\n\n"
        f"💡 Use /topvideos for most viewed"
    )
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def top_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not STATS["video_views"]:
        await update.message.reply_text("❌ No video views yet!")
        return
    
    sorted_videos = sorted(STATS["video_views"].items(), key=lambda x: x[1], reverse=True)[:10]
    
    top_list = []
    for idx, (vid_id, views) in enumerate(sorted_videos, 1):
        top_list.append(f"{idx}. <code>{vid_id}</code> - 👁 {views} views")
    
    top_text = "\n".join(top_list)
    
    await update.message.reply_text(
        f"🏆 <b>Top 10 Videos:</b>\n\n{top_text}",
        parse_mode=ParseMode.HTML
    )

async def users_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    await update.message.reply_text(
        f"👥 <b>Total Users: {len(STATS['total_users'])}</b>\n\n"
        f"📈 Active bot users",
        parse_mode=ParseMode.HTML
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 <b>Broadcast Message</b>\n\n"
            "Usage: /broadcast Your message here\n\n"
            "Message will be sent to all users!",
            parse_mode=ParseMode.HTML
        )
        return
    
    message = " ".join(context.args)
    success = 0
    failed = 0
    
    await update.message.reply_text("📤 Broadcasting... Please wait!")
    
    for user_id in STATS["total_users"]:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 <b>Broadcast Message:</b>\n\n{message}",
                parse_mode=ParseMode.HTML
            )
            success += 1
        except:
            failed += 1
    
    await update.message.reply_text(
        f"✅ <b>Broadcast Complete!</b>\n\n"
        f"✅ Successful: {success}\n"
        f"❌ Failed: {failed}",
        parse_mode=ParseMode.HTML
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # User commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("myactivity", my_activity))
    
    # Admin commands
    application.add_handler(CommandHandler("addvideo", add_video))
    application.add_handler(CommandHandler("videos", list_videos))
    application.add_handler(CommandHandler("search", search_video))
    application.add_handler(CommandHandler("delvideo", delete_video))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("topvideos", top_videos))
    application.add_handler(CommandHandler("users", users_count))
    application.add_handler(CommandHandler("broadcast", broadcast))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info(f"🚀 Bot started with {len(VIDEOS)} videos and {len(STATS['total_users'])} users!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
