#!/usr/bin/env python3
import os
import logging
import nest_asyncio
nest_asyncio.apply()  # Allows nested event loops

import asyncio
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token
TOKEN = "7960447841:AAGw_T6cuc2U3IvdzxJcTC1dmorP7iQZn7A"

# Channel details for forced joining
CHANNEL_ID = -1001859547091
FORCE_CHANNEL_URL = "https://t.me/+serfX9E4dDM1NGQ1"

# 🚫 Massive List of Banned Words
ILLEGAL_WORDS = [
    # 🔫 Gun Names
    "ak47", "m416", "awm", "scar-l", "ump45", "kar98k", "m24", "dp28", "uzi", "vector", "s12k", "s686",
    "p90", "glock", "m16", "m416", "desert eagle", "rpg", "m249", "mp5", "famas", "mp7", "m4 carbine",
    "sks", "f2000", "galil", "cz75", "m82", "thompson", "m4", "ak", "akm", "mac10", "bizon", "stechkin", "tavor", "hk416",
    # 🔞 NSFW Words
    "sex", "porn", "nude", "boobs", "dick", "penis", "vagina", "anal", "fuck", "suck", "busty", "orgasm",
    "threesome", "hardcore", "stripper", "camgirl", "nsfw", "cuckold", "incest", "milf", "deepthroat",
    "onlyfans", "bdsm", "hentai", "erotic", "cumshot", "lesbian", "chut", "lund", "lnd", "chodo", "gay porn", "feet pics", "naked", "escort",
    # 💰 Fraud & Scams
    "hacked", "cracked", "free uc", "mod apk", "cheat codes", "hacker", "scam", "carding", "fraud", "fake ids",
    "paypal logs", "bin generator", "stolen credit card", "free money", "deepweb", "tor market", "illegal logs",
    "cvv dump", "black market", "whatsapp bomber", "phishing", "paypal transfer", "fake passport",
    # 💊 Drugs & Dark Web
    "weed", "cocaine", "drugs", "ecstasy", "meth", "heroin", "opium", "xanax", "LSD", "crystal meth",
    "fentanyl", "mdma", "magic mushrooms", "lean", "marijuana", "ketamine", "adderall", "molly", "lsd tabs",
    # 💳 Financial Scams
    "bank logs", "money laundering", "cash app flip", "bitcoin scam", "stolen accounts", "free bitcoin",
    "paypal hack", "venmo hack", "western union scam", "gift card scam", "fake money", "fraudulent checks",
    # 🚨 Hacking & Illegal Software
    "sql injection", "bruteforce", "ddos attack", "rat tool", "trojan virus", "malware", "keylogger",
    "telegram spam bot", "darknet", "spyware", "facebook hack", "gmail hack", "ransomware", "rootkit",
    # 🇮🇳 Hindi & Slang Words
    "gand faad", "sexy", "sex", "fuck", "kill field", "gun lab", "gandu", "madarchod", "bhenchod", "mc", "bc"
]

# Global album tracking
album_cache = {}
album_flag = {}
album_task_scheduled = {}

async def process_album_deletion(media_group_id: str):
    await asyncio.sleep(2)  # Delay to collect album messages
    if album_flag.get(media_group_id, False):
        messages = album_cache.get(media_group_id, [])
        tasks = [msg.delete() for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Error deleting album message: {res}")
        logger.info(f"Deleted entire album (media_group_id: {media_group_id}) due to illegal content.")
    album_cache.pop(media_group_id, None)
    album_flag.pop(media_group_id, None)
    album_task_scheduled.pop(media_group_id, None)

async def delete_illegal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if message.media_group_id:
        media_group_id = message.media_group_id
        album_cache.setdefault(media_group_id, []).append(message)
        content = message.text or message.caption
        if content and any(word.lower() in content.lower() for word in ILLEGAL_WORDS):
            album_flag[media_group_id] = True
        if not album_task_scheduled.get(media_group_id, False):
            album_task_scheduled[media_group_id] = True
            asyncio.create_task(process_album_deletion(media_group_id))
        return
    else:
        content = message.text or message.caption
        if content and any(word.lower() in content.lower() for word in ILLEGAL_WORDS):
            try:
                await message.delete()
                logger.info("Deleted message containing banned words.")
            except Exception as e:
                logger.error(f"Error deleting message: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        # Check if the user is a member of the channel.
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status not in ["member", "administrator", "creator"]:
            raise Exception("User not a member")
    except Exception as e:
        keyboard = [
            [InlineKeyboardButton("ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ ", url=FORCE_CHANNEL_URL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 ʏᴏᴜ ᴍᴜꜱᴛ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ. ᴘʟᴇᴀꜱᴇ ᴊᴏɪɴ ᴀɴᴅ ᴛʜᴇɴ ᴘʀᴇꜱꜱ /start ᴀɢᴀɪɴ.",
            reply_markup=reply_markup
        )
        return

    # If the user is already a member, show the welcome message.
    me = await context.bot.get_me()
    bot_username = me.username

    welcome_text = (
        "<b>🚀 Welcome!\n\n"
        "I am a bot that automatically deletes messages containing banned words.\n"
        "✨ Features:\n"
        "• Deletes messages with illegal words, including entire albums\n"
        "• Works in both groups and channels\n"
        "• Prevents scam, NSFW, and gun-related content\n\n"
        "• Use /banwords to check banned words list.</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton("ᴀᴅᴅ ᴛᴏ ᴄʜᴀɴɴᴇʟ 📢", url=f"https://t.me/{bot_username}?startchannel=true"),
            InlineKeyboardButton("ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘꜱ 👥", url=f"https://t.me/{bot_username}?startgroup=true")
        ],
        [
            InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴘᴇʀ ✨", url="https://t.me/JODxPREDATOR")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

async def banwords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    words_list = "\n".join(f"• {word}" for word in ILLEGAL_WORDS)
    reply = f"<b>🚫 Banned Words:</b>\n{words_list}" if ILLEGAL_WORDS else "<b>No banned words are currently set.</b>"
    await update.message.reply_text(reply, parse_mode="HTML")

def run_flask_server():
    # Create a Flask app for health checks.
    app = Flask(__name__)

    @app.route('/')
    def index():
        logger.info("Index route '/' was hit.")
        return "Welcome to the bot server!", 200

    @app.route('/health')
    def health_check():
        logger.info("Health check '/health' was hit.")
        return "Bot is running", 200

    # Use the port provided by the environment variable.
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port)

async def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("banwords", banwords))
    application.add_handler(MessageHandler(filters.ALL, delete_illegal_message))
    logger.info("Telegram bot is running and monitoring messages...")
    await application.run_polling()

if __name__ == '__main__':
    # Start the Flask server in a separate thread for health checks.
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True
    flask_thread.start()

    # Run the Telegram bot.
    asyncio.run(main())
