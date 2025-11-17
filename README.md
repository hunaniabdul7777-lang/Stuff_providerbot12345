# Telegram Force Subscription Bot

Premium video content delivery bot with channel verification.

## Features

### User Features
- Force channel subscription
- Premium video delivery
- Personal activity statistics
- Help and support

### Admin Features
- Add/Delete videos
- List videos with view counts
- Search videos
- Bot statistics
- Top viewed videos
- User management
- Broadcast messages
- Database backup

## Installation

1. Clone repository
2. Install: pip install -r requirements.txt
3. Update bot.py with your token and channel IDs
4. Make bot admin in channels
5. Run: python bot.py

## Commands

### User Commands
- /start - Start bot
- /help - Help message
- /about - Bot info
- /myactivity - Your stats

### Admin Commands
- /addvideo - Add video
- /videos - List all videos
- /search - Search videos
- /delvideo - Delete video
- /stats - Bot statistics
- /topvideos - Most viewed
- /users - User count
- /recent - Recent activity
- /broadcast - Message all users
- /backup - Backup databases
- ## How to Add Videos

1. Send video to bot
2. Caption: /addvideo video_id
3. Bot gives share link
4. Post link in content channel

Example:
/addvideo movie_1

## Deployment

### Oracle Cloud (Free Forever)
1. Create Ubuntu VM
2. Clone repo
3. Install dependencies
4. Run with screen or systemd

### Railway/Render
1. Connect GitHub repo
2. Deploy as Background Worker

## Configuration

- BOT_TOKEN: From @BotFather
- REQUIRED_CHANNELS: Channel IDs
- CONTENT_CHANNEL: Your channel
- ADMIN_IDS: Your Telegram ID

Get channel ID: Use @RawDataBot or @JsonDumpBot

## Troubleshooting

Bot not responding?
- Check token
- Verify bot is running
- Check logs

Channel verification failing?
- Bot must be admin in channels
- Check channel IDs correct
- Verify usernames

## Support

Check logs and verify configuration.

Made for premium content delivery.
