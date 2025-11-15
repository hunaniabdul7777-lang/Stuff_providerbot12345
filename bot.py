import logging
import json
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# --------------------------
# YOUR SAME CONFIG
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
# Load & Save Video DB
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

VIDEOS = load_videos()

# --------------------------
# Bot Logic
# --------------------------

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for c in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=c["id"], user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # If link contains video ID
    if context.args:
        video_id = context.args[0]
        is_member = await check_membership(user_id, context)

        if not is_member:
            keyboard = [
                [InlineKeyboardButton(f"Join {c['name']}", url=f"https://t.me/{c['username'][1:]}")]
                for c in REQUIRED_CHANNELS
            ]
            keyboard.append([InlineKeyboardButton("Check Again", callback_data="check")])

            await update.message.reply_text(
                "⚠️ Please join required channels:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            context.user_data["pending"] = video_id
            return

        # Send video
        if video_id in VIDEOS:
            await update.message.reply_video(VIDEOS[video_id])
        else:
            await update.message.reply_text("Invalid video ID.")
        return

    await update.message.reply_text("Welcome! Send a valid video link.")


async def callback_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "check":
        ok = await check_membership(q.from_user.id, context)

        if ok:
            await q.edit_message_text("👍 Verified! Sending your video...")
            if "pending" in context.user_data:
                vid = context.user_data["pending"]
                if vid in VIDEOS:
                    await q.message.reply_video(VIDEOS[vid])
                del context.user_data["pending"]
        else:
            await q.answer("❌ Still not joined!", show_alert=True)


async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Unauthorized")

    if not update.message.video:
        return await update.message.reply_text("Send video with /addvideo ID")

    if not context.args:
        return await update.message.reply_text("ID missing")

    vid = context.args[0]
    file_id = update.message.video.file_id

    VIDEOS[vid] = file_id
    save_videos(VIDEOS)

    bot_user = await context.bot.get_me()
    link = f"https://t.me/{bot_user.username}?start={vid}"

    await update.message.reply_text(f"✔️ Added\nID: {vid}\nLink:\n{link}")


async def videos_list(update: Update
                      , context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Unauthorized")

    if not VIDEOS:
        return await update.message.reply_text("No videos")

    txt = "\n".join([f"- {v}" for v in VIDEOS.keys()])
    await update.message.reply_text(txt)


async def del_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Unauthorized")

    if not context.args:
        return await update.message.reply_text("Usage: /delvideo ID")

    vid = context.args[0]

    if vid in VIDEOS:
        del VIDEOS[vid]
        save_videos(VIDEOS)
        await update.message.reply_text("Deleted!")
    else:
        await update.message.reply_text("Not found.")


# --------------------------
# Flask + Webhook Setup
# --------------------------

app = Flask(__name__)

application = (
    Application.builder()
    .token(BOT_TOKEN)
    .build()
)

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("addvideo", add_video))
application.add_handler(CommandHandler("videos", videos_list))
application.add_handler(CommandHandler("delvideo", del_video))
application.add_handler(CallbackQueryHandler(callback_btn))

@app.route("/", methods=["GET"])
def home():
    return "Bot is Running", 200

@app.route("/webhook", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
