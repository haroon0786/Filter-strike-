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
CHANNEL_ID = -1002675485656
FORCE_CHANNEL_URL = "https://t.me/+oWVDU9f9Ggk5ZGE9"

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
    "gand faad", "sexy", "sex", "fuck", "kill field", "gun lab", "gandu", "madarchod", "bhenchod", "mc", "bc",
    # 🎨 Color Trading & Trading Related Words
    "color trading", "colour trading", "color game", "colour game", "color prediction", "colour prediction",
    "color bet", "colour bet", "red green", "win go", "wingo", "5d lottery", "k3 lottery", "trx win",
    "aviator", "crash game", "bcgame", "1xbet", "betway", "daman game", "91 club", "tc lottery",
    "big mumbai", "lottery sambad", "dear lottery", "nagaland lottery", "sikkim lottery", "kerala lottery",
    "rajshree lottery", "satta king", "satta matka", "matka boss", "kalyan matka", "mumbai matka",
    "dpboss", "sattaking", "fast result", "jodi chart", "panna", "single", "double patti", "triple patti",
    "teen patti", "andar bahar", "dragon tiger", "baccarat", "roulette", "blackjack", "poker",
    "slot machine", "jackpot", "casino", "gambling", "betting", "wagering", "bookmaker", "odds",
    "fantasy sports", "dream11", "mpl", "gamezy", "my11circle", "halaplay", "fanfight", "ballbaazi",
    "parimatch", "melbet", "mostbet", "crickex", "fairplay", "exchange", "cricket betting", "ipl betting",
    "match fixing", "inside news", "sure shot", "fixed match", "100% win", "guaranteed win", "leak news",
    "premium tips", "vip tips", "paid tips", "signal", "hack", "cheat", "trick", "loophole", "bug",
    "unlimited money", "free chips", "free coins", "generator", "mod", "cracked app", "unlocked",
    "referral code", "promo code", "bonus code", "invitation code", "agent", "promoter", "recruiter",
    "downline", "upline", "commission", "earning", "income", "profit", "loss recovery", "martingale",
    # Additional Trading Terms
    "binary options", "forex", "crypto trading", "day trading", "swing trading", "scalping", "leverage",
    "margin trading", "futures", "options", "derivatives", "pump dump", "insider trading", "penny stocks",
    "investment scheme", "ponzi", "pyramid scheme", "mlm", "network marketing", "get rich quick",
    "passive income", "easy money", "work from home", "online earning", "part time job", "full time income",
    "withdraw proof", "payment proof", "earning proof", "income proof", "bank statement", "screenshot",
    # Color Game Specific
    "big small", "odd even", "number prediction", "digit prediction", "lucky number", "magic number",
    "trend analysis", "pattern", "formula", "strategy", "method", "technique", "system", "algorithm",
    "auto bet", "robot", "bot trading", "signal bot", "prediction bot", "hack bot", "cheat bot"
]

# Global album tracking
album_cache = {}
album_flag = {}
album_task_scheduled = {}
album_banned_words = {}  # Track which words triggered the ban for albums

def find_banned_words(text):
    """Find all banned words in the given text"""
    if not text:
        return []
    
    text_lower = text.lower()
    found_words = []
    
    for word in ILLEGAL_WORDS:
        if word.lower() in text_lower:
            found_words.append(word)
    
    return found_words

async def process_album_deletion(media_group_id: str):
    await asyncio.sleep(2)  # Delay to collect album messages
    if album_flag.get(media_group_id, False):
        messages = album_cache.get(media_group_id, [])
        banned_words = album_banned_words.get(media_group_id, [])
        
        # Delete all messages in the album
        tasks = [msg.delete() for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        deleted_count = 0
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Error deleting album message: {res}")
            else:
                deleted_count += 1
        
        # Send notification about album deletion
        if messages and banned_words:
            chat_id = messages[0].chat_id
            user_name = messages[0].from_user.first_name if messages[0].from_user else "Unknown"
            banned_words_str = ", ".join(banned_words[:5])  # Show max 5 words
            
            notification_text = (
                f"🚫 <b>Album Deleted!</b>\n\n"
                f"👤 User: {user_name}\n"
                f"📸 Messages deleted: {deleted_count}\n"
                f"🔍 Banned words found: <code>{banned_words_str}</code>\n"
                f"⚠️ Reason: Contains prohibited content"
            )
            
            try:
                # Get the bot instance from the first message's context
                from telegram import Bot
                bot = Bot(token=TOKEN)
                await bot.send_message(
                    chat_id=chat_id,
                    text=notification_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error sending album deletion notification: {e}")
        
        logger.info(f"Deleted entire album (media_group_id: {media_group_id}) due to illegal content: {banned_words}")
    
    # Cleanup
    album_cache.pop(media_group_id, None)
    album_flag.pop(media_group_id, None)
    album_task_scheduled.pop(media_group_id, None)
    album_banned_words.pop(media_group_id, None)

async def delete_illegal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if message.media_group_id:
        # Handle album messages
        media_group_id = message.media_group_id
        album_cache.setdefault(media_group_id, []).append(message)
        
        content = message.text or message.caption
        banned_words = find_banned_words(content)
        
        if banned_words:
            album_flag[media_group_id] = True
            # Store banned words for this album
            existing_words = album_banned_words.get(media_group_id, [])
            album_banned_words[media_group_id] = list(set(existing_words + banned_words))
        
        if not album_task_scheduled.get(media_group_id, False):
            album_task_scheduled[media_group_id] = True
            asyncio.create_task(process_album_deletion(media_group_id))
        return
    else:
        # Handle single messages
        content = message.text or message.caption
        banned_words = find_banned_words(content)
        
        if banned_words:
            try:
                # Delete the original message
                await message.delete()
                
                # Send notification about deletion
                user_name = message.from_user.first_name if message.from_user else "Unknown"
                banned_words_str = ", ".join(banned_words[:5])  # Show max 5 words
                
                notification_text = (
                    f"🚫 <b>Message Deleted!</b>\n\n"
                    f"👤 User: {user_name}\n"
                    f"🔍 Banned words found: <code>{banned_words_str}</code>\n"
                    f"⚠️ Reason: Contains prohibited content"
                    f"⛔ Action: Deleted to protect the channel"
                )
                
                # Send the notification
                notification_msg = await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=notification_text,
                    parse_mode="HTML"
                )
                
                # Auto-delete the notification after 10 seconds
                asyncio.create_task(delete_notification_after_delay(notification_msg, 10))
                
                logger.info(f"Deleted message from {user_name} containing banned words: {banned_words}")
                
            except Exception as e:
                logger.error(f"Error deleting message: {e}")

async def delete_notification_after_delay(message, delay_seconds):
    """Delete notification message after specified delay"""
    try:
        await asyncio.sleep(delay_seconds)
        await message.delete()
    except Exception as e:
        logger.error(f"Error deleting notification message: {e}")

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
        "• Deletes messages with illegal words\n"
        "• Works in both groups and channels\n"
        "• Prevents scam, NSFW, gun-related, and trading content\n"
        "• Shows notification when messages are deleted\n"
        "• Use /banwords to check banned words list.</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton("ᴀᴅᴅ ᴛᴏ ᴄʜᴀɴɴᴇʟ 📢", url=f"https://t.me/{bot_username}?startchannel=true"),
            InlineKeyboardButton("ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘꜱ 👥", url=f"https://t.me/{bot_username}?startgroup=true")
        ],
        [
            InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴘᴇʀ ✨", url="https://t.me/ogxcodex")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

async def banwords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Group words by category for better display
    categories = {
        "🔫 Gun Names": ["ak47", "m416", "awm", "scar-l", "ump45", "kar98k", "m24", "dp28", "uzi", "vector"],
        "🔞 NSFW": ["sex", "porn", "nude", "fuck", "nsfw", "erotic"],
        "💰 Fraud & Scams": ["hacked", "cracked", "scam", "carding", "fraud", "phishing"],
        "🎨 Color Trading": ["color trading", "colour trading", "satta king", "matka", "aviator", "casino"],
        "💊 Drugs": ["weed", "cocaine", "drugs", "meth", "heroin"],
        "🚨 Hacking": ["sql injection", "malware", "keylogger", "trojan", "ransomware"]
    }
    
    reply = "<b>🚫 Banned Words Categories:</b>\n\n"
    for category, words in categories.items():
        reply += f"{category}\n"
        reply += "\n".join(f"• {word}" for word in words[:5])  # Show first 5 words
        reply += f"\n... and {len([w for w in ILLEGAL_WORDS if any(sample in w for sample in words)]) - 5} more\n\n"
    
    reply += f"<b>Total banned words: {len(ILLEGAL_WORDS)}</b>"
    
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
