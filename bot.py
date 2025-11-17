import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# ========== CONFIGURATION ==========
BOT_TOKEN = "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA"

REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "@stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "@stuffprovider_proofs", "id": -1001963037939}
]

CONTENT_CHANNEL = "@stuffprovider_demo"
ADMIN_IDS = [5967565554]

DB_FILE = "videos_db.json"
STATS_FILE = "stats_db.json"

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== DATABASE FUNCTIONS ==========
def load_videos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} videos")
                return data
        except:
            return {}
    return {}

def save_videos(videos):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(videos, f, indent=2)
        logger.info(f"Saved {len(videos)} videos")
        return True
    except Exception as e:
        logger.error(f"Error saving: {e}")
        return False

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data.get("total_users"), list):
                    data["total_users"] = set(data["total_users"])
                return data
        except:
            pass
    return {"total_users": set(), "video_views": {}, "user_activity": {}}

def save_stats(stats):
    try:
        stats_copy = stats.copy()
        stats_copy["total_users"] = list(stats["total_users"])
        with open(STATS_FILE, 'w') as f:
            json.dump(stats_copy, f, indent=2)
        return True
    except:
        return False

VIDEOS = load_videos()
STATS = load_stats()

# ========== TRACKING ==========
def track_user(user_id):
    try:
        STATS["total_users"].add(user_id)
        user_str = str(user_id)
        if user_str not in STATS["user_activity"]:
            STATS["user_activity"][user_str] = {
                "first_seen": datetime.now().isoformat(),
                "total_requests": 0,
                "videos_watched": 0
            }
        STATS["user_activity"][user_str]["total_requests"] += 1
        STATS["user_activity"][user_str]["last_seen"] = datetime.now().isoformat()
        save_stats(STATS)
    except:
        pass

def track_video_view(video_id, user_id):
    try:
        if video_id not in STATS["video_views"]:
            STATS["video_views"][video_id] = 0
        STATS["video_views"][video_id] += 1
        
        user_str = str(user_id)
        if user_str in STATS["user_activity"]:
            STATS["user_activity"][user_str]["videos_watched"] += 1
        save_stats(STATS)
    except:
        pass

# ========== MEMBERSHIP CHECK ==========
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    not_joined = []
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_joined.append(channel)
        except:
            not_joined.append(channel)
    return (len(not_joined) == 0, not_joined)

# ========== START COMMAND ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    track_user(user_id)
    
    if context.args:
        video_id = context.args[0]
        is_member, not_joined = await check_membership(user_id, context)
        
        if not is_member:
            keyboard = []
            for channel in not_joined:
                keyboard.append([InlineKeyboardButton(f"✅ Join {channel['name']}", url=f"https://t.me/{channel['username'][1:]}")])
            keyboard.append([InlineKeyboardButton("✔️ Verify", callback_data=f"check_{video_id}")])
            
            await update.message.reply_text(
                "🔒 <b>Access Denied!</b>\n\nPehle channels join karo:\n\n⚠️ Saare channels zaroori hain!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
        
        if video_id in VIDEOS:
            try:
                track_video_view(video_id, user_id)
                await update.message.reply_video(
                    video=VIDEOS[video_id],
                    caption=f"✅ <b>Enjoy!</b>\n\n🔔 {CONTENT_CHANNEL}",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {str(e)}")
        else:
            await update.message.reply_text("❌ Invalid video link!")
    else:
        is_member, not_joined = await check_membership(user_id, context)
        
        if not is_member:
            keyboard = []
            for channel in not_joined:
                keyboard.append([InlineKeyboardButton(f"✅ Join {channel['name']}", url=f"https://t.me/{channel['username'][1:]}")])
            keyboard.append([InlineKeyboardButton("✔️ Verify", callback_data="check_membership")])
            
            await update.message.reply_text(
                f"👋 <b>Welcome {user.first_name}!</b>\n\n"
                f"🎬 Premium Video Bot\n\n"
                f"Channels join karo:\n"
                f"1️⃣ {REQUIRED_CHANNELS[0]['username']}\n"
                f"2️⃣ {REQUIRED_CHANNELS[1]['username']}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        else:
            keyboard = [
                [InlineKeyboardButton("📢 Content", url=f"https://t.me/{CONTENT_CHANNEL[1:]}")],
                [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
            ]
            await update.message.reply_text(
                f"✅ <b>Welcome {user.first_name}!</b>\n\n"
                f"Access granted!\n\n"
                f"📢 {CONTENT_CHANNEL} se links click karo!\n\n"
                f"💡 /help for commands",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )

# ========== HELP COMMAND ==========
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in ADMIN_IDS:
        text = (
            "👑 <b>ADMIN COMMANDS</b>\n\n"
            "📹 Videos:\n"
            "/addvideo /videos /delvideo /search\n\n"
            "📊 Stats:\n"
            "/stats /topvideos /users /recent\n\n"
            "📢 Other:\n"
            "/broadcast /backup\n\n"
            "👤 User:\n"
            "/start /help /about /myactivity"
        )
    else:
        text = (
            "ℹ️ <b>COMMANDS</b>\n\n"
            "/start - Start bot\n"
            "/help - This message\n"
            "/about - Bot info\n"
            "/myactivity - Your stats"
        )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ========== ABOUT COMMAND ==========
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_views = sum(STATS["video_views"].values())
    text = (
        f"🤖 <b>ABOUT BOT</b>\n\n"
        f"👥 Users: {len(STATS['total_users'])}\n"
        f"🎥 Videos: {len(VIDEOS)}\n"
        f"👁 Views: {total_views}\n\n"
        f"📢 Channel: {CONTENT_CHANNEL}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ========== MY ACTIVITY ==========
async def my_activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in STATS["user_activity"]:
        activity = STATS["user_activity"][user_id]
        first = datetime.fromisoformat(activity["first_seen"]).strftime("%d %b %Y")
        last = datetime.fromisoformat(activity["last_seen"]).strftime("%d %b, %I:%M %p")
        
        text = (
            f"📊 <b>YOUR ACTIVITY</b>\n\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📅 First: {first}\n"
            f"🕐 Last: {last}\n"
            f"📈 Requests: {activity['total_requests']}\n"
            f"🎬 Videos: {activity.get('videos_watched', 0)}"
        )
    else:
        text = "❌ No activity data!"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ========== BUTTON CALLBACK ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "check_membership":
        is_member, _ = await check_membership(user_id, context)
        if is_member:
            await query.edit_message_text(
                f"✅ <b>Verified!</b>\n\n📢 {CONTENT_CHANNEL} se links click karo!",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.answer("❌ Channels join nahi kiye!", show_alert=True)
    
    elif data.startswith("check_"):
        video_id = data.replace("check_", "")
        is_member, _ = await check_membership(user_id, context)
        
        if is_member and video_id in VIDEOS:
            track_video_view(video_id, user_id)
            await query.message.reply_video(
                video=VIDEOS[video_id],
                caption=f"✅ Video!",
                parse_mode=ParseMode.HTML
            )
            await query.edit_message_text("✅ Video sent!")
        else:
            await query.answer("❌ Error!", show_alert=True)
    
    elif data == "help":
        await help_command(update, context)

# ========== ADD VIDEO ==========
async def add_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not update.message.video:
        await update.message.reply_text(
            "📹 Send video with caption:\n/addvideo video_id",
            parse_mode=ParseMode.HTML
        )
        return
    
    if not context.args:
        await update.message.reply_text("❌ Missing video ID!")
        return
    
    video_id = context.args[0]
    
    if video_id in VIDEOS:
        await update.message.reply_text(f"⚠️ ID exists: <code>{video_id}</code>", parse_mode=ParseMode.HTML)
        return
    
    file_id = update.message.video.file_id
    VIDEOS[video_id] = file_id
    
    if save_videos(VIDEOS):
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={video_id}"
        
        await update.message.reply_text(
            f"✅ <b>Video Added!</b>\n\n"
            f"🆔 ID: <code>{video_id}</code>\n"
            f"🔗 Link:\n<code>{link}</code>\n\n"
            f"📊 Total: {len(VIDEOS)}",
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Video added: {video_id}")
    else:
        await update.message.reply_text("❌ Save error!")

# ========== LIST VIDEOS ==========
async def list_videos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not VIDEOS:
        await update.message.reply_text("❌ No videos!")
        return
    
    video_list = []
    for idx, vid_id in enumerate(sorted(VIDEOS.keys())[:30], 1):
        views = STATS["video_views"].get(vid_id, 0)
        video_list.append(f"{idx}. <code>{vid_id}</code> - 👁 {views}")
    
    text = "\n".join(video_list)
    await update.message.reply_text(
        f"📹 <b>Videos ({len(VIDEOS)}):</b>\n\n{text}",
        parse_mode=ParseMode.HTML
    )

# ========== SEARCH VIDEO ==========
async def search_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /search keyword")
        return
    
    keyword = " ".join(context.args).lower()
    results = [v for v in VIDEOS.keys() if keyword in v.lower()]
    
    if results:
        text = "\n".join([f"• <code>{v}</code>" for v in results[:20]])
        await update.message.reply_text(
            f"🔍 <b>Results ({len(results)}):</b>\n\n{text}",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("❌ No results!")

# ========== DELETE VIDEO ==========
async def delete_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /delvideo video_id")
        return
    
    video_id = context.args[0]
    
    if video_id in VIDEOS:
        del VIDEOS[video_id]
        save_videos(VIDEOS)
        await update.message.reply_text(
            f"✅ Deleted: <code>{video_id}</code>\n\nRemaining: {len(VIDEOS)}",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("❌ Not found!")

# ========== STATS ==========
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    total_views = sum(STATS["video_views"].values())
    avg = total_views // len(VIDEOS) if VIDEOS else 0
    
    text = (
        f"📊 <b>STATS</b>\n\n"
        f"👥 Users: {len(STATS['total_users'])}\n"
        f"🎥 Videos: {len(VIDEOS)}\n"
        f"👁 Views: {total_views}\n"
        f"📈 Avg: {avg}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ========== TOP VIDEOS ==========
async def top_videos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not STATS["video_views"]:
        await update.message.reply_text("❌ No views yet!")
        return
    
    sorted_vids = sorted(STATS["video_views"].items(), key=lambda x: x[1], reverse=True)[:10]
    
    top_list = []
    for idx, (vid, views) in enumerate(sorted_vids, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        top_list.append(f"{medal} <code>{vid}</code> - {views}")
    
    text = "\n".join(top_list)
    await update.message.reply_text(f"🏆 <b>TOP 10:</b>\n\n{text}", parse_mode=ParseMode.HTML)

# ========== USERS COUNT ==========
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    await update.message.reply_text(
        f"👥 <b>Total Users: {len(STATS['total_users'])}</b>",
        parse_mode=ParseMode.HTML
    )

# ========== RECENT ACTIVITY ==========
async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    recent = sorted(
        STATS['user_activity'].items(),
        key=lambda x: x[1].get('last_seen', ''),
        reverse=True
    )[:10]
    
    if not recent:
        await update.message.reply_text("❌ No activity!")
        return
    
    recent_list = []
    for uid, act in recent:
        last = datetime.fromisoformat(act['last_seen'])
        mins = (datetime.now() - last).seconds // 60
        time_str = f"{mins}m" if mins < 60 else f"{mins//60}h"
        recent_list.append(f"• <code>{uid}</code> - {time_str} ago")
    
    text = "\n".join(recent_list)
    await update.message.reply_text(f"🕐 <b>RECENT:</b>\n\n{text}", parse_mode=ParseMode.HTML)

# ========== BROADCAST ==========
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast message")
        return
    
    message = " ".join(context.args)
    success = 0
    
    await update.message.reply_text("📤 Broadcasting...")
    
    for uid in STATS["total_users"]:
        try:
            await context.bot.send_message(uid, f"📢 {message}")
            success += 1
        except:
            pass
    
    await update.message.reply_text(f"✅ Sent to {success} users!")

# ========== BACKUP ==========
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    try:
        await update.message.reply_document(
            document=open(DB_FILE, 'rb'),
            caption=f"📁 Videos: {len(VIDEOS)}"
        )
        await update.message.reply_document(
            document=open(STATS_FILE, 'rb'),
            caption=f"📊 Users: {len(STATS['total_users'])}"
        )
        await update.message.reply_text("✅ Backup done!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ========== MAIN ==========
def main():
    logger.info("=" * 50)
    logger.info("🤖 Bot Starting...")
    logger.info(f"📊 Videos: {len(VIDEOS)}")
    logger.info(f"👥 Users: {len(STATS['total_users'])}")
    logger.info("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("myactivity", my_activity_command))
    
    # Admin commands
    app.add_handler(CommandHandler("addvideo", add_video_command))
    app.add_handler(CommandHandler("videos", list_videos_command))
    app.add_handler(CommandHandler("search", search_video_command))
    app.add_handler(CommandHandler("delvideo", delete_video_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("topvideos", top_videos_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("backup", backup_command))
    
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("✅ Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
