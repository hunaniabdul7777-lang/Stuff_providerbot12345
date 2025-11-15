# Railway Deployment Package

## File 1: bot.py
```python
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
import os

# Bot configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8529436226:AAEVYIFRyy57y2fUvTnlEzk65baYnmnJuNA")
REQUIRED_CHANNELS = [
    {"name": "Stuff Provider Demo", "username": "@stuffprovider_demo", "id": -1003340238856},
    {"name": "Stuff Provider Proofs", "username": "@stuffprovider_proofs", "id": -1001963037939}
]
CONTENT_CHANNEL = "@stuffprovider_demo"
ADMIN_IDS = [5967565554]

VIDEOS = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            logger.error(f"Error checking membership: {e}")
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
            keyboard.append([InlineKeyboardButton("✔️ Done! Check Again", callback_data="check_membership")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🔒 <b>Access Denied!</b>\n\n"
                "Pehle neeche diye channels join karo, phir 'Check Again' button dabao:\n\n"
                "⚠️ <b>Important:</b> Saare channels join karna zaroori hai!",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            context.user_data['pending_video'] = video_id
            return
        
        if video_id in VIDEOS:
            try:
                await update.message.reply_video(
                    video=VIDEOS[video_id],
                    caption=f"✅ <b>Yeh lo aapki video!</b>\n\n🔔 More content: {CONTENT_CHANNEL}",
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
            keyboard.append([InlineKeyboardButton("✔️ Done! Check Again", callback_data="check_membership")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"👋 <b>Welcome {user.first_name}!</b>\n\n"
                f"🔒 Bot use karne ke liye pehle yeh channels join karo:\n\n"
                f"1️⃣ {REQUIRED_CHANNELS[0]['username']}\n"
                f"2️⃣ {REQUIRED_CHANNELS[1]['username']}\n\n"
                f"✅ Channels join karne ke baad 'Check Again' dabao!",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        else:
            keyboard = [[InlineKeyboardButton("📢 Content Channel", url=f"https://t.me/{CONTENT_CHANNEL[1:]}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"✅ <b>Access Granted!</b>\n\n"
                f"Aap ab bot use kar sakte ho!\n\n"
                f"📢 Videos ke liye {CONTENT_CHANNEL} join karo aur wahan se links click karo!",
                reply_markup=reply_markup,
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
                f"✅ <b>Verified!</b>\n\n"
                f"Aap ab bot use kar sakte ho!\n\n"
                f"📢 Videos ke liye {CONTENT_CHANNEL} channel se links click karo!",
                parse_mode=ParseMode.HTML
            )
            
            if 'pending_video' in context.user_data:
                video_id = context.user_data['pending_video']
                if video_id in VIDEOS:
                    await query.message.reply_video(
                        video=VIDEOS[video_id],
                        caption=f"✅ <b>Yeh lo aapki video!</b>\n\n🔔 More content: {CONTENT_CHANNEL}",
                        parse_mode=ParseMode.HTML
                    )
                del context.user_data['pending_video']
        else:
            await query.answer("❌ Abhi bhi channels join nahi kiye!", show_alert=True)

async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not update.message.video:
        await update.message.reply_text(
            "📹 <b>How to add video:</b>\n\n"
            "1. Video bhejo\n"
            "2. Caption: /addvideo video_id\n\n"
            "Example: /addvideo video_3",
            parse_mode=ParseMode.HTML
        )
        return
    
    if not context.args:
        await update.message.reply_text("❌ Video ID missing!")
        return
    
    video_id = context.args[0]
    file_id = update.message.video.file_id
    VIDEOS[video_id] = file_id
    
    bot_username = (await context.bot.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={video_id}"
    
    await update.message.reply_text(
        f"✅ <b>Video Added!</b>\n\n"
        f"🆔 ID: <code>{video_id}</code>\n"
        f"🔗 Link:\n<code>{share_link}</code>\n\n"
        f"Is link ko channel mein share karo!",
        parse_mode=ParseMode.HTML
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addvideo", add_video))
    application.add_handler(CallbackQueryHandler(button_callback))
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

## File 2: requirements.txt
```
python-telegram-bot==21.5
```

## File 3: Procfile
```
worker: python bot.py
```

## File 4: runtime.txt
```
python-3.11.0
```

---

# Deployment Instructions

## Method 1: Using GitHub (Recommended)

1. **Create GitHub Repository:**
   - Go to github.com
   - Click "New Repository"
   - Name: `telegram-bot`
   - Make it Public
   - Click "Create Repository"

2. **Upload Files:**
   - Click "uploading an existing file"
   - Upload all 4 files (bot.py, requirements.txt, Procfile, runtime.txt)
   - Click "Commit changes"

3. **Deploy on Railway:**
   - Go to railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Select your `telegram-bot` repository
   - Railway will auto-deploy!

## Method 2: Using Railway CLI (Advanced)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

---

# Post-Deployment

1. Bot automatically 24/7 chalega
2. Railway dashboard mein logs dekh sakte ho
3. Video add karne ke liye bot ko message karo
4. Channels mein bot ko admin banana mat bhoolna!

✅ Done! Your bot is live 24/7!
