import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===========================================
# 🔥 YOUR BOT SETTINGS (Already Added)
# ===========================================
BOT_TOKEN = "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA"

REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "stuffprovider_proofs", "id": -1001963037939}
]

ADMIN_IDS = [5967565554]

WEBHOOK_URL = os.environ.get(
    "WEBHOOK_URL",
    "https://your-render-url.onrender.com/webhook"
)

# Video database (memory only)
VIDEOS = {
    "v1": "YOUR_FILE_ID_1",
    "v2": "YOUR_FILE_ID_2"
}

app = Flask(__name__)

# Telegram Application
application = Application.builder().token(BOT_TOKEN).build()


# ===========================================
# 🔹 CHECK CHANNEL JOIN
# ===========================================
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    for c in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(c["id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True


# ===========================================
# 🔹 START COMMAND
# ===========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if context.args:
        vid = context.args[0]

        is_joined = await check_membership(user.id, context)
        if not is_joined:
            kb = []
            for c in REQUIRED_CHANNELS:
                kb.append([InlineKeyboardButton(f"Join {c['name']}", url=f"https://t.me/{c['username']}")])

            kb.append([InlineKeyboardButton("Check Again", callback_data="recheck")])

            await update.message.reply_text(
                "⚠ You must join required channels:",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            context.user_data["pending"] = vid
            return

        # Joined → Send video
        if vid in VIDEOS:
            await update.message.reply_video(VIDEOS[vid])
        else:
            await update.message.reply_text("❌ Invalid ID")
        return

    await update.message.reply_text("Bot is working!")


# ===========================================
# 🔹 VERIFY BUTTON
# ===========================================
async def button(update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "recheck":
        is_joined = await check_membership(q.from_user.id, context)

        if not is_joined:
            await q.answer("❌ Still not joined!", show_alert=True)
            return

        await q.edit_message_text("✅ Verified! Open your link again.")

        if "pending" in context.user_data:
            vid = context.user_data["pending"]
            if vid in VIDEOS:
                await q.message.reply_video(VIDEOS[vid])
            del context.user_data["pending"]


# ===========================================
# 🔹 ADMIN COMMAND – ADD VIDEO
# ===========================================
async def addvideo(update, context):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("❌ Unauthorized")

    if not update.message.video:
        return await update.message.reply_text("Send video with /addvideo id")

    if not context.args:
        return await update.message.reply_text("❌ Provide ID")

    vid = context.args[0]
    file_id = update.message.video.file_id

    VIDEOS[vid] = file_id

    link = f"https://t.me/{(await context.bot.get_me()).username}?start={vid}"

    await update.message.reply_text(f"✅ Added!\nID: {vid}\nLink:\n{link}")


# ===========================================
# 🔹 REGISTER HANDLERS
# ===========================================
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("addvideo", addvideo))
application.add_handler(CallbackQueryHandler(button))


# ===========================================
# 🔹 WEBHOOK ROUTE
# ===========================================
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200


# ===========================================
# 🔹 RUN SERVER + SET WEBHOOK
# ===========================================
if __name__ == "__main__":
    import asyncio

    async def setup():
        await application.bot.set_webhook(WEBHOOK_URL)

    asyncio.run(setup())

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
