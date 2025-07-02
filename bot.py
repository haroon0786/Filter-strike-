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

# 🚫 Massive List of Banned Words (Enhanced with Trading Terms)
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
    
    # 🚀 Drugs & Dark Web
    "weed", "cocaine", "drugs", "ecstasy", "meth", "heroin", "opium", "xanax", "LSD", "crystal meth",
    "fentanyl", "mdma", "magic mushrooms", "lean", "marijuana", "ketamine", "adderall", "molly", "lsd tabs",
    
    # 💳 Financial Scams
    "bank logs", "money laundering", "cash app flip", "bitcoin scam", "stolen accounts", "free bitcoin",
    "paypal hack", "venmo hack", "western union scam", "gift card scam", "fake money", "fraudulent checks",
    
    # 🔨 Hacking & Illegal Software
    "sql injection", "bruteforce", "ddos attack", "rat tool", "trojan virus", "malware", "keylogger",
    "telegram spam bot", "darknet", "spyware", "facebook hack", "gmail hack", "ransomware", "rootkit",
    
    # 🇮🇳 Hindi & Slang Words
    "gand faad", "sexy", "sex", "fuck", "kill field", "gun lab", "gandu", "madarchod", "bhenchod", "mc", "bc",
    
    # 🎮 Color Trading & Gaming Scams (NEW ADDITIONS)
    "color trading", "colour trading", "color prediction", "colour prediction", "color game", "colour game",
    "91 club", "daman games", "tc lottery", "big mumbai", "lottery sambad", "dear lottery", "nagaland lottery",
    "sikkim lottery", "kerala lottery", "punjab lottery", "goa lottery", "mizoram lottery", "manipur lottery",
    "arunachal lottery", "meghalaya lottery", "assam lottery", "west bengal lottery", "odisha lottery",
    "jharkhand lottery", "chhattisgarh lottery", "madhya pradesh lottery", "rajasthan lottery", "haryana lottery",
    "punjab state lottery", "himachal lottery", "uttarakhand lottery", "uttar pradesh lottery", "bihar lottery",
    "tripura lottery", "andhra pradesh lottery", "telangana lottery", "karnataka lottery", "tamil nadu lottery",
    
    # 🎯 Trading & Betting Terms
    "satta", "matka", "kalyan matka", "mumbai matka", "rajdhani matka", "time bazar", "milan day", "milan night",
    "main mumbai", "new worli", "kuber morning", "madhur day", "madhur night", "gold ank", "super fast",
    "rajdhani day", "rajdhani night", "kalyan", "worli matka", "diamond matka", "golden matka", "fix game",
    "sure shot", "100% sure", "guaranteed win", "leak number", "inside news", "fix match", "match fixing",
    "teen patti", "andar bahar", "dragon tiger", "baccarat", "roulette", "blackjack", "poker", "casino",
    "betting", "gambling", "bet365", "1xbet", "parimatch", "betway", "melbet", "22bet", "mostbet",
    
    # 💎 Cryptocurrency Scams
    "pump and dump", "rug pull", "fake ico", "ponzi scheme", "pyramid scheme", "mlm scam", "binary options",
    "forex scam", "trading signals", "guaranteed profit", "risk free trading", "auto trading bot",
    "crypto mining scam", "fake exchange", "exit scam", "honeypot token", "fake airdrop",
    
    # 🎪 Online Gaming Fraud
    "pubg hack", "free fire hack", "cod hack", "valorant hack", "csgo hack", "apex hack", "fortnite hack",
    "minecraft hack", "roblox hack", "among us hack", "fall guys hack", "rocket league hack",
    "aimbot", "wallhack", "esp hack", "speed hack", "god mode", "unlimited ammo", "no recoil",
    "auto headshot", "magic bullet", "x ray vision", "fly hack", "teleport hack"
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

async def send_deletion_notification(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: str, detected_words: list):
    """Send notification to channel when a message is deleted"""
    try:
        notification_text = (
            f"🚫 **Message Deleted**\n\n"
            f"👤 **User:** {user_info}\n"
            f"💬 **Chat ID:** `{chat_id}`\n"
            f"🔍 **Detected Words:** {', '.join(detected_words)}\n"
            f"⏰ **Time:** {asyncio.get_event_loop().time()}\n\n"
            f"✅ **Action:** Message automatically deleted to protect the channel."
        )
        
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=notification_text,
            parse_mode="Markdown"
        )
        logger.info(f"Sent deletion notification to channel for user: {user_info}")
    except Exception as e:
        logger.error(f"Error sending deletion notification: {e}")

async def delete_illegal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    
    # Create user info string
    user_info = f"@{user.username}" if user.username else f"{user.first_name} (ID: {user.id})"
    
    if message.media_group_id:
        media_group_id = message.media_group_id
        album_cache.setdefault(media_group_id, []).append(message)
        content = message.text or message.caption
        
        if content:
            detected_words = [word for word in ILLEGAL_WORDS if word.lower() in content.lower()]
            if detected_words:
                album_flag[media_group_id] = True
                # Send notification for album deletion
                await send_deletion_notification(context, chat.id, user_info, detected_words)
        
        if not album_task_scheduled.get(media_group_id, False):
            album_task_scheduled[media_group_id] = True
            asyncio.create_task(process_album_deletion(media_group_id))
        return
    else:
        content = message.text or message.caption
        if content:
            detected_words = [word for word in ILLEGAL_WORDS if word.lower() in content.lower()]
            if detected_words:
                try:
                    await message.delete()
                    logger.info(f"Deleted message containing banned words: {detected_words}")
                    
                    # Send notification to channel
                    await send_deletion_notification(context, chat.id, user_info, detected_words)
                    
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
            "🚫 ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ʙᴇғᴏʀᴇ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ. ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴀɴᴅ ᴛʜᴇɴ ᴛʀʏ /start ᴀɢᴀɪɴ.",
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
        "• Prevents scam, NSFW, gun-related, and trading content\n"
        "• Sends notifications to channel when content is deleted\n\n"
        "• Use /banwords to check banned words list.</b>"
    )

    keyboard = [
        [
            InlineKeyboardButton("ᴀᴅᴅ ᴍᴇ ᴛᴏ ᴄʜᴀɴɴᴇʟ 🔒", url=f"https://t.me/{bot_username}?startchannel=true"),
            InlineKeyboardButton("ᴀᴅᴅ ᴍᴇ ɪɴ ɢʀᴏᴜᴘs 👥", url=f"https://t.me/{bot_username}?startgroup=true")
        ],
        [
            InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴘᴇʀ ✨", url="https://t.me/JODxPREDATOR")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

async def banwords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Split words into categories for better readability
    gun_words = [word for word in ILLEGAL_WORDS if any(gun in word for gun in ["ak", "m4", "gun", "rifle", "pistol"])]
    trading_words = [word for word in ILLEGAL_WORDS if any(trade in word for trade in ["trading", "matka", "satta", "lottery", "color", "colour"])]
    nsfw_words = [word for word in ILLEGAL_WORDS if any(nsfw in word for nsfw in ["sex", "porn", "nude", "fuck"])]
    
    words_text = (
        f"<b>🚫 Banned Words Categories:</b>\n\n"
        f"<b>🔫 Weapons ({len(gun_words)} words):</b>\n"
        f"• {', '.join(gun_words[:10])}{'...' if len(gun_words) > 10 else ''}\n\n"
        f"<b>🎮 Trading/Gambling ({len(trading_words)} words):</b>\n"
        f"• {', '.join(trading_words[:10])}{'...' if len(trading_words) > 10 else ''}\n\n"
        f"<b>🔞 NSFW ({len(nsfw_words)} words):</b>\n"
        f"• {', '.join(nsfw_words[:5])}{'...' if len(nsfw_words) > 5 else ''}\n\n"
        f"<b>📊 Total Banned Words: {len(ILLEGAL_WORDS)}</b>\n\n"
        f"<i>Note: This is a partial list. The bot monitors for all categories including scams, drugs, hacking tools, and more
