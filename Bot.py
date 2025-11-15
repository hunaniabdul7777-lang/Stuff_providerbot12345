import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# ==========================
#  BOT CONFIG
# ==========================
BOT_TOKEN = "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA"

REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "stuffprovider_proofs", "id": -1001963037939}
]

CONTENT_CHANNEL = "@stuffprovider_demo"
ADMIN_IDS = [5967565554]

DB_FILE = "videos_db.json"

# ==========================
#  LOGGING
# ==========================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==========================
#  VIDEO DATABASE
# ==========================
def load_videos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_videos(videos):
    with open(DB_FILE, "w") as f:
        json.dump(videos, f, indent=2)
    logger.info(f"[DB] Saved {len(videos)} videos")

VIDEOS = load_videos()
logger.info(f"[DB] Loaded {len(VIDEOS)} videos")


# ==========================
#  CHECK MEMBERSHIP
# ==========================
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel["id"], user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except:
            return False
    return True


# ==========================
#  JOIN BUTTON GENERATOR
# ==========================
def join_keyboard():
    keyboard = [
        [InlineKeyboardButton(f"🔗 Join {c['name']}", url=f"https://t.me/{c['username']}")]
        for c in REQUIRED_CHANNELS
    ]
    keyboard.append([InlineKeyboardButton("✔️ Check Again", callback_data="check_membership")])
    return InlineKeyboardMarkup(keyboard)


# ==========================
#  START COMMAND
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if context.args:
        video_id = context.args[0]

        is_member = await check_membership(user_id, context)
        if not is_member:
            await update.message.reply_text(
                "🔒 <b>Access Locked!</b>\n\nPehle dono channels join karo!",
                reply_markup=join_keyboard(),
                parse_mode=ParseMode.HTML
            )
            context.user_data["pending_video"] = video_id
            return

        # Send video
        if video_id in VIDEOS:
            await update.message.reply_video(
                VIDEOS[video_id],
                caption=f"🎬 <b>Your Video</b>\n🔔 More: {CONTENT_CHANNEL}",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ Invalid video link!")
        return

    # No arguments → Normal start
    is_member = await check_membership(user_id, context)
    if not is_member:
        await update.message.reply_text(
            f"👋 Welcome {user.first_name}!\n\n🔒 Channels join karo to access content!",
            reply_markup=join_keyboard(),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            f"✅ Access Granted!\nClick any demo link from {CONTENT_CHANNEL}",
            parse_mode=ParseMode.HTML
        )


# ==========================
#  CALLBACK BUTTON HANDLER
# ==========================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if query.data == "check_membership":
        is_member = await check_membership(user_id, context)

        if not is_member:
            await query.answer("❌ Channels join nahi kiye!", show_alert=True)
            return

        await query.edit_message_text(
            f"✅ Verified!\nNow click demo links from {CONTENT_CHANNEL}",
            parse_mode=ParseMode.HTML
        )

        # Send pending video
        if "pending_video" in context.user_data:
            v_id = context.user_data["pending_video"]
            if v_id in VIDEOS:
                await query.message.reply_video(
                    VIDEOS[v_id],
                    caption=f"🎥 <b>Video</b>\n🔔 {CONTENT_CHANNEL}",
                    parse_mode=ParseMode.HTML
                )
            del context.user_data["pending_video"]


# ==========================
#  ADD VIDEO (ADMIN ONLY)
# ==========================
async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return

    if not update.message.video:
        await update.message.reply_text(
            "📹 <b>How to Add Video:</b>\n\n"
            "Send video with caption:\n\n"
            "<code>/addvideo video_id</code>",
            parse_mode=ParseMode.HTML
        )
        return

    if not context.args:
        await update.message.reply_text("❌ Video ID missing!")
        return

    video_id = context.args[0]
    file_id = update.message.video.file_id

    VIDEOS[video_id] = file_id
    save_videos(VIDEOS)

    bot_user = await context.bot.get_me()
    share_link = f"https://t.me/{bot_user.username}?start={video_id}"

    await update.message.reply_text(
        f"✅ <b>Video Saved!</b>\n\n"
        f"🆔 ID: <code>{video_id}</code>\n"
        f"🔗 Link:\n<code>{share_link}</code>\n\n"
        f"📊 Total Videos: {len(VIDEOS)}",
        parse_mode=ParseMode.HTML
    )


# ==========================
#  LIST VIDEOS
# ==========================
async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return

    if not VIDEOS:
        await update.message.reply_text("❌ No videos in database!")
        return

    msg = "\n".join([f"• <code>{v}</code>" for v in VIDEOS.keys()])
    await update.message.reply_text(
        f"📹 <b>All Videos ({len(VIDEOS)}):</b>\n\n{msg}",
        parse_mode=ParseMode.HTML
    )


# ==========================
#  DELETE VIDEO
# ==========================
async def delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /delvideo video_id")
        return

    video_id = context.args[0]
    if video_id not in VIDEOS:
        await update.message.reply_text("❌ Video not found!")
        return

    del VIDEOS[video_id]
    save_videos(VIDEOS)

    await update.message.reply_text(
        f"🗑 Deleted <code>{video_id}</code>\nRemaining: {len(VIDEOS)}",
        parse_mode=ParseMode.HTML
    )


# ==========================
#  RUN BOT
# ==========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addvideo", add_video))
    app.add_handler(CommandHandler("videos", list_videos))
    app.add_handler(CommandHandler("delvideo", delete_video))
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info(f"Bot started with {len(VIDEOS)} videos")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
