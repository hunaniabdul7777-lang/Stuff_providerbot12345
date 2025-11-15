import os
import json
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# ------------------ CONFIG ------------------
BOT_TOKEN = "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA"

REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "@stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "@stuffprovider_proofs", "id": -1001963037939}
]

CONTENT_CHANNEL = "@stuffprovider_demo"
ADMIN_IDS = [5967565554]

DB_FILE = "videos_db.json"
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL") + "/webhook"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- DB ----------------
def load_videos():
    if os.path.exists(DB_FILE):
        try:
            return json.load(open(DB_FILE))
        except:
            return {}
    return {}

def save_videos(v):
    json.dump(v, open(DB_FILE, "w"))
    logger.info("Saved video DB")

VIDEOS = load_videos()

# ---------------- FUNCTIONS ----------------
async def check_membership(user_id, context):
    for channel in REQUIRED_CHANNELS:
        try:
            m = await context.bot.get_chat_member(channel["id"], user_id)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if context.args:
        vid = context.args[0]
        allowed = await check_membership(user_id, context)

        if not allowed:
            keyboard = [
                [InlineKeyboardButton(f"Join {c['name']}", url=f"https://t.me/{c['username'][1:]}")]
                for c in REQUIRED_CHANNELS
            ]
            keyboard.append([InlineKeyboardButton("Check Again", callback_data="check")])

            context.user_data["pending"] = vid
            return await update.message.reply_text("Join channels first:", reply_markup=InlineKeyboardMarkup(keyboard))

        if vid in VIDEOS:
            return await update.message.reply_video(VIDEOS[vid])
        else:
            return await update.message.reply_text("Invalid ID")

    await update.message.reply_text("Bot ready. Open a valid link.")


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    ok = await check_membership(q.from_user.id, context)

    if not ok:
        return await q.answer("Not joined!", show_alert=True)

    await q.edit_message_text("Verified! Sending video…")

    if "pending" in context.user_data:
        vid = context.user_data["pending"]
        if vid in VIDEOS:
            await q.message.reply_video(VIDEOS[vid])
        del context.user_data["pending"]


async def addvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Unauthorized")

    if not update.message.video:
        return await update.message.reply_text("Send video with /addvideo ID")

    if not context.args:
        return await update.message.reply_text("Missing ID")

    vid = context.args[0]
    file_id = update.message.video.file_id

    VIDEOS[vid] = file_id
    save_videos(VIDEOS)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={vid}"

    await update.message.reply_text(f"Added!\n\nID: {vid}\nLink:\n{link}")


async def listvideos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Unauthorized")

    if not VIDEOS:
        return await update.message.reply_text("Empty.")

    await update.message.reply_text("\n".join(VIDEOS.keys()))


async def delvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("Unauthorized")

    if not context.args:
        return await update.message.reply_text("Usage: /delvideo ID")

    vid = context.args[0]
    if vid in VIDEOS:
        del VIDEOS[vid]
        save_videos(VIDEOS)
        return await update.message.reply_text("Deleted.")
    return await update.message.reply_text("Not found")


# ---------------- WEBHOOK SERVER ----------------
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("addvideo", addvideo))
application.add_handler(CommandHandler("videos", listvideos))
application.add_handler(CommandHandler("delvideo", delvideo))
application.add_handler(CallbackQueryHandler(callback))


@app.post("/webhook")
async def process():
    data = request.get_json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok", 200


@app.get("/")
def home():
    return "Bot is running on webhook", 200


if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        application.bot.set_webhook(WEBHOOK_URL)
    )
    app.run(host="0.0.0.0", port=10000)
