import logging
import json
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from telegram.constants import ParseMode

# --------------------------
# SAME CONFIG AS YOUR OLD BOT
# --------------------------

BOT_TOKEN = "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA"

REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "@stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "@stuffprovider_proofs", "id": -1001963037939}
]

CONTENT_CHANNEL = "@stuffprovider_demo"
ADMIN_IDS = [5967565554]

DB_FILE = "videos_db.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------
# Load & Save Database
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
    logger.info(f"Videos saved: {len(videos)}")

VIDEOS = load_videos()


# --------------------------
# Bot Functions (UNCHANGED)
# --------------------------

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # /start videoID
    if context.args:
        video_id = context.args[0]
        is_member = await check_membership(user_id, context)

        if not is_member:
            keyboard = [
                [InlineKeyboardButton(f"Join {c['name']}", url=f"https://t.me/{c['username'][1:]}")]
                for c in REQUIRED_CHANNELS
            ]
            keyboard.append([InlineKeyboardButton("Check Again", callback_data="check_membership")])

            await update.message.reply_text(
                "Join required channels:", reply_markup=InlineKeyboardMarkup(keyboard)
            )

            context.user_data['pending_video'] = video_id
            return

        # Send video
        if video_id in VIDEOS:
            await update.message.reply_video(VIDEOS[video_id])
        else:
            await update.message.reply_text("Invalid video ID.")
        return

    await update.message.reply_text("Welcome! Send a valid video link.")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_membership":
        is_member = await check_membership(query.from_user.id, context)

        if is_member:
            await query.edit_message_text("Verified! Now open your video link.")

            if 'pending_video' in context.user_data:
                vid = context.user_data['pending_video']
                if vid in VIDEOS:
                    await query.message.reply_video(VIDEOS[vid])
                del context.user_data['pending_video']

        else:
            await query.answer("Not joined!", show_alert=True)


async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Unauthorized.")

    if not update.message.video:
        return await update.message.reply_text("Send video with /addvideo ID")

    if not context.args:
        return await update.message.reply_text("ID missing.")

    video_id = context.args[0]
    file_id = update.message.video.file_id

    VIDEOS[video_id] = file_id
    save_videos(VIDEOS)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={video_id}"

    await update.message.reply_text(f"Added!\nID: {video_id}\nLink:\n{link}")


async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Unauthorized.")

    if not VIDEOS:
        return await update.message.reply_text("No videos.")

    text = "\n".join([f"- {v}" for v in VIDEOS.keys()])
    await update.message.reply_text(text)


async def delete_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Unauthorized.")

    if not context.args:
        return await update.message.reply_text("Usage: /delvideo ID")

    vid = context.args[0]
    if vid in VIDEOS:
        del VIDEOS[vid]
        save_videos(VIDEOS)
        await update.message.reply_text("Deleted.")
    else:
        await update.message.reply_text("Not found.")


# --------------------------
# FLASK + WEBHOOK
# --------------------------

app = Flask(__name__)

application = Application.builder().token(BOT_TOKEN).build()

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("addvideo", add_video))
application.add_handler(CommandHandler("videos", list_videos))
application.add_handler(CommandHandler("delvideo", delete_video))
application.add_handler(CallbackQueryHandler(button_callback))


@app.get("/")
def home():
    return "Bot running!", 200


@app.post("/webhook")
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok", 200


# Start Flask (Render)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook"
        )
