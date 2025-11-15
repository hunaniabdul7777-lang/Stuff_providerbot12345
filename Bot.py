import logging
import json
import os
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

# Database file
DB_FILE = "videos_db.json"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load videos from database
def load_videos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

# Save videos to database
def save_videos(videos):
    with open(DB_FILE, 'w') as f:
        json.dump(videos, f, indent=2)
    logger.info(f"Videos saved! Total: {len(videos)}")

# Load videos at startup
VIDEOS = load_videos()
logger.info(f"Loaded {len(VIDEOS)} videos from database")

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
                await update.message.reply_video(
                    video=VIDEOS[video_id],
                    caption=f"✅ <b>Video!</b>\n\n🔔 More: {CONTENT_CHANNEL}",
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
                f"👋 <b>Welcome {user.first_name}!</b>\n\n🔒 Channels join karo:\n\n1️⃣ {REQUIRED_CHANNELS[0]['username']}\n2️⃣ {REQUIRED_CHANNELS[1]['username']}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                f"✅ <b>Access Granted!</b>\n\n📢 {CONTENT_CHANNEL} se links click karo!",
                parse_mode=ParseMode.HTML
            )

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
                    await query.message.reply_video(
                        video=VIDEOS[video_id],
                        caption=f"✅ <b>Video!</b>\n\n🔔 {CONTENT_CHANNEL}",
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
        await update.message.reply_text(
            "📹 <b>How to add video:</b>\n\n"
            "1. Video bhejo\n"
            "2. Caption: /addvideo video_id\n\n"
            "Example: /addvideo movie_1",
            parse_mode=ParseMode.HTML
        )
        return
    
    if not context.args:
        await update.message.reply_text("❌ Video ID missing!")
        return
    
    video_id = context.args[0]
    file_id = update.message.video.file_id
    
    # Save to memory and database
    VIDEOS[video_id] = file_id
    save_videos(VIDEOS)
    
    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={video_id}"
    
    await update.message.reply_text(
        f"✅ <b>Video Added Successfully!</b>\n\n"
        f"🆔 Video ID: <code>{video_id}</code>\n"
        f"🔗 Share Link:\n<code>{share_link}</code>\n\n"
        f"📊 Total videos: {len(VIDEOS)}\n\n"
        f"Is link ko channel mein share karo!",
        parse_mode=ParseMode.HTML
    )

async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not VIDEOS:
        await update.message.reply_text("❌ No videos added yet!")
        return
    
    video_list = "\n".join([f"• <code>{vid_id}</code>" for vid_id in VIDEOS.keys()])
    
    await update.message.reply_text(
        f"📹 <b>All Videos ({len(VIDEOS)}):</b>\n\n{video_list}",
        parse_mode=ParseMode.HTML
    )

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
            f"✅ Video <code>{video_id}</code> deleted!\n\n"
            f"📊 Remaining: {len(VIDEOS)} videos",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("❌ Video not found!")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addvideo", add_video))
    application.add_handler(CommandHandler("videos", list_videos))
    application.add_handler(CommandHandler("delvideo", delete_video))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info(f"Bot started with {len(VIDEOS)} videos in database!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
