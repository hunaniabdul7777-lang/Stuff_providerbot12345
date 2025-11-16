import logging
import json
import os
from datetime import datetime
from threading import Thread
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    filters,
    MessageHandler
)
from telegram.constants import ParseMode

# ============================================
# CONFIGURATION
# ============================================
BOT_TOKEN = "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA"
REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "@stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "@stuffprovider_proofs", "id": -1001963037939}
]
CONTENT_CHANNEL = "@stuffprovider_demo"
ADMIN_IDS = [5967565554]

DB_FILE = "videos_db.json"
STATS_FILE = "stats_db.json"

# ============================================
# FLASK APP (Web Interface)
# ============================================
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "bot": "Stuff Provider Bot",
        "version": "2.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "uptime": "ok"})

@app.route('/stats')
def web_stats():
    """Public stats endpoint"""
    return jsonify({
        "total_users": len(STATS['total_users']),
        "total_videos": len(VIDEOS),
        "total_views": sum(STATS["video_views"].values())
    })

# ============================================
# LOGGING SETUP
# ============================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# DATABASE FUNCTIONS
# ============================================
def load_videos():
    """Load videos database"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading videos: {e}")
            return {}
    return {}

def save_videos(videos):
    """Save videos database"""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(videos)} videos to database")
    except Exception as e:
        logger.error(f"Error saving videos: {e}")

def load_stats():
    """Load statistics database"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data["total_users"] = set(data.get("total_users", []))
                return data
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
    return {
        "total_users": set(),
        "video_views": {},
        "user_activity": {},
        "daily_stats": {}
    }

def save_stats(stats):
    """Save statistics database"""
    try:
        stats_copy = stats.copy()
        stats_copy["total_users"] = list(stats["total_users"])
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats_copy, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving stats: {e}")

# Initialize databases
VIDEOS = load_videos()
STATS = load_stats()
logger.info(f"✅ Loaded {len(VIDEOS)} videos and {len(STATS['total_users'])} users")

# ============================================
# TRACKING & ANALYTICS
# ============================================
def track_user(user_id, username=None):
    """Track user activity"""
    STATS["total_users"].add(user_id)
    uid = str(user_id)
    
    if uid not in STATS["user_activity"]:
        STATS["user_activity"][uid] = {
            "first_seen": datetime.now().isoformat(),
            "total_requests": 0,
            "username": username
        }
    
    STATS["user_activity"][uid]["total_requests"] += 1
    STATS["user_activity"][uid]["last_seen"] = datetime.now().isoformat()
    if username:
        STATS["user_activity"][uid]["username"] = username
    
    # Daily stats
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in STATS.get("daily_stats", {}):
        STATS.setdefault("daily_stats", {})[today] = {"users": set(), "requests": 0}
    STATS["daily_stats"][today]["users"].add(user_id)
    STATS["daily_stats"][today]["requests"] += 1
    
    save_stats(STATS)

def track_video_view(video_id):
    """Track video views"""
    if video_id not in STATS["video_views"]:
        STATS["video_views"][video_id] = 0
    STATS["video_views"][video_id] += 1
    save_stats(STATS)

# ============================================
# MEMBERSHIP CHECK
# ============================================
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is member of required channels"""
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                logger.info(f"User {user_id} not member of {channel['name']}")
                return False
        except Exception as e:
            logger.error(f"Membership check error for {channel['name']}: {e}")
            return False
    return True

def create_join_keyboard():
    """Create join channels keyboard"""
    keyboard = [
        [InlineKeyboardButton(f"✅ Join {c['name']}", url=f"https://t.me/{c['username'][1:]}")] 
        for c in REQUIRED_CHANNELS
    ]
    keyboard.append([InlineKeyboardButton("🔄 Check Again", callback_data="check_membership")])
    return InlineKeyboardMarkup(keyboard)

# ============================================
# USER COMMANDS
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username
    track_user(user_id, username)
    
    logger.info(f"Start command received from user {user_id}")

    # Deep link handler
    if context.args:
        video_id = context.args[0]
        logger.info(f"Deep link with video_id: {video_id}")
        is_member = await check_membership(user_id, context)
        
        if not is_member:
            context.user_data['pending_video'] = video_id
            await update.message.reply_text(
                f"👋 <b>Hey {user.first_name}!</b>\n\n"
                "🔒 <b>Access Denied!</b>\n"
                "Pehle niche diye gaye channels join karo, phir 'Check Again' button dabao!\n\n"
                "✨ <i>Unlimited videos dekho after joining!</i>",
                reply_markup=create_join_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return
        
        # Send video if member
        if video_id in VIDEOS:
            track_video_view(video_id)
            await update.message.reply_video(
                video=VIDEOS[video_id],
                caption=f"✅ <b>Enjoy your video!</b>\n\n"
                        f"🔔 More videos: {CONTENT_CHANNEL}\n"
                        f"👥 Share with friends!",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Video {video_id} sent to user {user_id}")
        else:
            await update.message.reply_text(
                "❌ <b>Invalid Link!</b>\n\n"
                f"Nayi video links ke liye {CONTENT_CHANNEL} check karo!",
                parse_mode=ParseMode.HTML
            )
    else:
        # Regular start command
        is_member = await check_membership(user_id, context)
        
        if not is_member:
            await update.message.reply_text(
                f"👋 <b>Welcome {user.first_name}!</b>\n\n"
                "🎥 <b>Unlimited Videos Access ke liye:</b>\n"
                "1️⃣ Niche diye channels join karo\n"
                "2️⃣ 'Check Again' button dabao\n"
                "3️⃣ Videos enjoy karo! 🍿\n\n"
                "💡 <i>100% free hai!</i>",
                reply_markup=create_join_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                f"✅ <b>Welcome Back, {user.first_name}!</b>\n\n"
                f"🎬 <b>Access Granted!</b>\n"
                f"📢 {CONTENT_CHANNEL} se video links click karo!\n\n"
                "📋 Commands:\n"
                "• /help - Bot commands\n"
                "• /about - Bot info\n"
                "• /myactivity - Your stats\n\n"
                "🎉 <i>Enjoy unlimited videos!</i>",
                parse_mode=ParseMode.HTML
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user_id = update.effective_user.id
    logger.info(f"Help command received from user {user_id}")
    
    if user_id in ADMIN_IDS:
        help_text = (
            "👑 <b>Admin Commands:</b>\n\n"
            "📹 <b>Video Management:</b>\n"
            "• /addvideo [id] - Add new video (send video with caption)\n"
            "• /delvideo [id] - Delete video\n"
            "• /videos - List all videos\n"
            "• /topvideos - Most viewed videos\n\n"
            "📊 <b>Analytics:</b>\n"
            "• /stats - Bot statistics\n"
            "• /dailystats - Daily analytics\n"
            "• /users - User list\n\n"
            "📢 <b>Communication:</b>\n"
            "• /broadcast [msg] - Send to all users"
        )
    else:
        help_text = (
            "ℹ️ <b>User Commands:</b>\n\n"
            "• /start - Start bot\n"
            "• /help - Show this help\n"
            "• /about - Bot information\n"
            "• /myactivity - Your activity stats\n\n"
            f"📢 Get videos from: {CONTENT_CHANNEL}\n"
            "💡 Click video links to watch!"
        )
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command"""
    logger.info(f"About command received from user {update.effective_user.id}")
    total_views = sum(STATS["video_views"].values())
    
    about_text = (
        "🤖 <b>Stuff Provider Bot</b>\n\n"
        f"👥 Total Users: {len(STATS['total_users'])}\n"
        f"🎥 Total Videos: {len(VIDEOS)}\n"
        f"👀 Total Views: {total_views}\n\n"
        "🔥 <b>Features:</b>\n"
        "• Unlimited video access\n"
        "• Channel-based verification\n"
        "• Fast video delivery\n"
        "• Regular updates\n\n"
        f"📢 Channel: {CONTENT_CHANNEL}"
    )
    
    await update.message.reply_text(about_text, parse_mode=ParseMode.HTML)

async def my_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myactivity command"""
    uid = str(update.effective_user.id)
    logger.info(f"Activity command received from user {uid}")
    activity = STATS["user_activity"].get(uid)
    
    if activity:
        first_seen = datetime.fromisoformat(activity['first_seen']).strftime("%d %b %Y")
        activity_text = (
            "📊 <b>Your Activity Stats:</b>\n\n"
            f"📅 Member Since: {first_seen}\n"
            f"🔢 Total Requests: {activity['total_requests']}\n"
            f"📺 Videos Watched: Available soon\n\n"
            "✨ <i>Keep enjoying videos!</i>"
        )
    else:
        activity_text = "❌ <b>No activity data found!</b>\n\nStart watching videos to see stats."
    
    await update.message.reply_text(activity_text, parse_mode=ParseMode.HTML)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    logger.info(f"Button callback from user {user_id}: {query.data}")
    
    if query.data == "check_membership":
        is_member = await check_membership(user_id, context)
        
        if is_member:
            await query.edit_message_text(
                f"✅ <b>Verified Successfully!</b>\n\n"
                f"🎉 Ab tum videos dekh sakte ho!\n"
                f"📢 {CONTENT_CHANNEL} pe jao aur video links click karo!\n\n"
                "💡 Enjoy unlimited content! 🍿",
                parse_mode=ParseMode.HTML
            )
            
            # Send pending video if exists
            if 'pending_video' in context.user_data:
                vid = context.user_data['pending_video']
                if vid in VIDEOS:
                    track_video_view(vid)
                    await query.message.reply_video(
                        VIDEOS[vid],
                        caption=f"✅ <b>Here's your video!</b>\n\n🔔 {CONTENT_CHANNEL}",
                        parse_mode=ParseMode.HTML
                    )
                del context.user_data['pending_video']
        else:
            await query.answer(
                "❌ Abhi bhi channels join nahi kiye! Pehle join karo.",
                show_alert=True
            )

# ============================================
# ADMIN COMMANDS
# ============================================
async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new video - Admin only"""
    user_id = update.effective_user.id
    logger.info(f"Add video command from user {user_id}")
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized access!")
        return
    
    if not update.message.video:
        await update.message.reply_text(
            "📹 <b>Usage:</b>\n"
            "1. Send a video\n"
            "2. Add caption: <code>/addvideo video_id</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    if not context.args:
        await update.message.reply_text("❌ Video ID missing! Use: /addvideo [id]")
        return
    
    vid_id = context.args[0]
    VIDEOS[vid_id] = update.message.video.file_id
    save_videos(VIDEOS)
    
    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={vid_id}"
    
    await update.message.reply_text(
        f"✅ <b>Video Added Successfully!</b>\n\n"
        f"🆔 Video ID: <code>{vid_id}</code>\n"
        f"🔗 Share Link:\n<code>{share_link}</code>\n\n"
        f"📊 Total Videos: {len(VIDEOS)}",
        parse_mode=ParseMode.HTML
    )
    logger.info(f"Admin {user_id} added video {vid_id}")

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all videos - Admin only"""
    user_id = update.effective_user.id
    logger.info(f"List videos command from user {user_id}")
    
    if user_id not in ADMIN_IDS:
        return
    
    if not VIDEOS:
        await update.message.reply_text("❌ No videos in database!")
        return
    
    video_list = "\n".join([f"• <code>{vid}</code>" for vid in list(VIDEOS.keys())[:50]])
    
    await update.message.reply_text(
        f"📹 <b>Video Database ({len(VIDEOS)} videos):</b>\n\n{video_list}",
        parse_mode=ParseMode.HTML
    )

async def delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete video - Admin only"""
    user_id = update.effective_user.id
    logger.info(f"Delete video command from user {user_id}")
    
    if user_id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /delvideo [video_id]")
        return
    
    vid = context.args[0]
    
    if vid in VIDEOS:
        del VIDEOS[vid]
        save_videos(VIDEOS)
        await update.message.reply_text(
            f"✅ <b>Video Deleted!</b>\n\n"
            f"🗑️ Removed: <code>{vid}</code>\n"
            f"📊 Remaining: {len(VIDEOS)} videos",
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Admin deleted video {vid}")
    else:
        await update.message.reply_text(f"❌ Video ID <code>{vid}</code> not found!", parse_mode=ParseMode.HTML)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics - Admin only"""
    user_id = update.effective_user.id
    logger.info(f"Stats command from user {user_id}")
    
    if user_id not in ADMIN_IDS:
        return
    
    total_views = sum(STATS["video_views"].values())
    total_requests = sum(u.get("total_requests", 0) for u in STATS["user_activity"].values())
    
    stats_text = (
        "📊 <b>Bot Statistics:</b>\n\n"
        f"👥 Total Users: {len(STATS['total_users'])}\n"
        f"🎥 Total Videos: {len(VIDEOS)}\n"
        f"👀 Total Views: {total_views}\n"
        f"📊 Total Requests: {total_requests}\n"
        f"📅 Database Size: {len(STATS['user_activity'])} users tracked"
    )
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def daily_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show daily statistics - Admin only"""
    user_id = update.effective_user.id
    logger.info(f"Daily stats command from user {user_id}")
    
    if user_id not in ADMIN_IDS:
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    daily = STATS.get("daily_stats", {}).get(today, {"users": set(), "requests": 0})
    
    stats_text = (
        f"📅 <b>Today's Statistics ({today}):</b>\n\n"
        f"👥 Active Users: {len(daily.get('users', set()))}\n"
        f"📊 Total Requests: {daily.get('requests', 0)}"
    )
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def top_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top viewed videos - Admin only"""
    user_id = update.effective_user.id
    logger.info(f"Top videos command from user {user_id}")
    
    if user_id not in ADMIN_IDS:
        return
    
    if not STATS["video_views"]:
        await update.message.reply_text("❌ No video views yet!")
        return
    
    sorted_vids = sorted(STATS["video_views"].items(), key=lambda x: x[1], reverse=True)[:10]
    text = "\n".join([f"{i+1}. <code>{v}</code> - {c} views" for i, (v, c) in enumerate(sorted_vids)])
    
    await update.message.reply_text(
        f"🏆 <b>Top 10 Videos:</b>\n\n{text}",
        parse_mode=ParseMode.HTML
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users - Admin only"""
    user_id = update.effective_user.id
    logger.info(f"Broadcast command from user {user_id}")
    
    if user_id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 <b>Usage:</b>\n<code>/broadcast Your message here</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    msg = " ".join(context.args)
    success = 0
    failed = 0
    
    status_msg = await update.message.reply_text("📤 Broadcasting... 0%")
    
    total_users = len(STATS["total_users"])
    for i, user_id in enumerate(STATS["total_users"]):
        try:
            await context.bot.send_message(
                user_id,
                f"📢 <b>Announcement:</b>\n\n{msg}",
                parse_mode=ParseMode.HTML
            )
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed for {user_id}: {e}")
        
        # Update progress every 10 users
        if i % 10 == 0:
            progress = int((i / total_users) * 100)
            try:
                await status_msg.edit_text(f"📤 Broadcasting... {progress}%")
            except:
                pass
    
    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete!</b>\n\n"
   
