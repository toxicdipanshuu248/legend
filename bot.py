#!/usr/bin/env python3
"""
ᚔ᚜ 𓆩『𓍼ֶָ֢˖ ࣪ꨄ𝐃⃝𝛆‌֟፝𝛎 .་༘࿐』𓆪 ᚛ᚔ
┌──『 𓍼ֶָ֢˖ 𝐏ʀᴏꜰɪʟᴇ ˖ֶָ֢𓍼』 ──┐
│ ̼͙̼͙̈́͆̈́ͯ̒̆̀̓ͧ̈́͆̈́ͯ̒̆̀̓ͧ͠͠ᯓ   𝐌ᴀꜱᴛᴇʀ :: 𝐀ᴅᴍɪɴ 
"""

import asyncio
import json
import os
import random
import signal
import sys
import time
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from pathlib import Path
import logging
import base64 as _b64
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import RetryAfter, TimedOut, NetworkError
import traceback

# ==================== FIX UNICODE ====================
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==================== KEEP-ALIVE SERVER (Anti-Sleep) ====================
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"DEV Matrix Cluster is Alive 24/7")
    
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get('PORT', 8080))
    try:
        server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
        server.serve_forever()
    except Exception as e:
        print(f"⚠️ Keep-alive server port in use or failed: {e}")

def keep_alive():
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()

# ==================== PERSISTENCE (Lightweight) ====================
DB_PATH = "bot_data.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS active_chats
                    (chat_id INTEGER PRIMARY KEY, target TEXT, attack_type TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS admins
                    (user_id INTEGER PRIMARY KEY)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS settings
                    (key TEXT PRIMARY KEY, value TEXT)''')
        self.conn.commit()
    
    def save_active(self, chat_id, target, attack_type):
        self.c.execute("INSERT OR REPLACE INTO active_chats VALUES (?, ?, ?)", 
                      (chat_id, target, attack_type))
        self.conn.commit()
    
    def remove_active(self, chat_id):
        self.c.execute("DELETE FROM active_chats WHERE chat_id = ?", (chat_id,))
        self.conn.commit()
    
    def get_active(self):
        self.c.execute("SELECT chat_id, target, attack_type FROM active_chats")
        return self.c.fetchall()
    
    def save_admin(self, user_id):
        self.c.execute("INSERT OR IGNORE INTO admins VALUES (?)", (user_id,))
        self.conn.commit()
    
    def get_admins(self):
        self.c.execute("SELECT user_id FROM admins")
        return {row[0] for row in self.c.fetchall()}
    
    def save_setting(self, key, value):
        self.c.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, json.dumps(value)))
        self.conn.commit()
    
    def get_setting(self, key, default=None):
        self.c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = self.c.fetchone()
        return json.loads(row[0]) if row else default

db = Database()

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== UPDATED TOKENS (9 Bots) ====================
TOKENS = [
    "8863613544:AAEVU9mo8tSurqYXvBNBTbZYLtHuAqNzveI",
    "8690627423:AAHQU3tQbqPuJFKDMS853I4RNcF7xaKzbl4",
    "8949972279:AAHoSlEBiqD_tY5MQlBHRGx97TT0uGaXdQc",
    "8628388492:AAEDkdEvW1WrsZB8F6UZyJXm6jw6gb93kSI",
    "8801267375:AAEQZZxaq_JWBNLhLwYuCQRxCQO9JsHjI6I",
    "8952360437:AAHYVHqdZc6fj3u-sQ4ygIFilh88yCbOmHs",
    "8846226909:AAENuQnNICGFdaM6EJDim_vhyk663KSTJco",
    "8844810422:AAGk7HJMR3tAv1_elbpoMOMWhoZc7PLeC5A",
    "8593398735:AAFhteHcnrPV9V1xsy0XGBDuiZa6J8XgZ9g",
]

# ==================== OWNERS ====================
_K_LIST = [
    _b64.b64decode(" Njk4MTE5Mjg0NA==").decode(),  # 6981192844
    _b64.b64decode(" NTIwNjU1NDgwNA==").decode(),  # 5206554804 (Naya ID Add Kar Diya)
]

def only_ownr(func):
    async def wrapper(update, context):
        if str(update.effective_user.id) not in _K_LIST:
            return await update.message.reply_text("❌ Access Denied - Owners Only")
        return await func(update, context)
    return wrapper

# ==================== EMOJIS ====================
EMOJIS = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❤️‍🔥", "❤️‍🩹", "💖", "💗", "💓", "💞", "💕", "💟", "❣️", "💘", "💝", "💌", "♥️"]

# ==================== CONTROLLER (Anti-Flood Optimized) ====================
class Controller:
    def __init__(self):
        self.attacks = {}
        self.stop_flags = {}
        self.bots = []
        self.admins = db.get_admins()
        self.master = db.get_setting("master", None)
        self.speed = db.get_setting("speed", 0.05)
        self.nc_counter = {}
        self.nc_limit = db.get_setting("nc_limit", 15)
        
        for owner in _K_LIST:
            self.admins.add(int(owner))
            db.save_admin(int(owner))
    
    def is_admin(self, user_id):
        return user_id in self.admins or user_id == self.master
    
    def stop_all(self):
        for chat_id in list(self.attacks.keys()):
            if chat_id not in self.stop_flags:
                self.stop_flags[chat_id] = {}
            for task_id, task in self.attacks[chat_id].items():
                self.stop_flags[chat_id][task_id] = True
                task.cancel()
            self.attacks[chat_id] = {}
            db.remove_active(chat_id)
            if chat_id in self.nc_counter:
                del self.nc_counter[chat_id]
    
    def stop_chat(self, chat_id):
        if chat_id in self.attacks:
            if chat_id not in self.stop_flags:
                self.stop_flags[chat_id] = {}
            for task_id, task in self.attacks[chat_id].items():
                self.stop_flags[chat_id][task_id] = True
                task.cancel()
            self.attacks[chat_id] = {}
            db.remove_active(chat_id)
            if chat_id in self.nc_counter:
                del self.nc_counter[chat_id]
    
    def should_stop(self, chat_id, task_id):
        return self.stop_flags.get(chat_id, {}).get(task_id, False)

controller = Controller()

# ==================== ROTATIONAL ANTI-FLOOD LOOPS ====================
async def nc_loop(bot, chat_id, target, task_id, bot_index, total_bots):
    last_emoji = None
    db.save_active(chat_id, target, "nc")
    
    try:
        while True:
            if controller.should_stop(chat_id, task_id):
                break
            
            await asyncio.sleep(bot_index * 0.4)
            
            emoji = random.choice([e for e in EMOJIS if e != last_emoji])
            last_emoji = emoji
            msg = f"{emoji} {target} {emoji}"
            
            try:
                await bot.set_chat_title(chat_id=chat_id, title=msg[:255])
                logger.info(f"✨ [DEV System] Bot #{bot_index+1} updated title successfully")
            except RetryAfter as e:
                wait_time = e.retry_after + random.uniform(1.0, 3.0)
                logger.warning(f"⚠️ FloodWait hit on Bot #{bot_index+1}: Sleeping for {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
            except Exception as e:
                error = str(e).lower()
                if "flood" in error or "too many requests" in error:
                    await asyncio.sleep(10)
                else:
                    pass
            
            await asyncio.sleep(max(controller.speed, 2.0))
    except asyncio.CancelledError:
        pass
    except Exception:
        pass
    finally:
        db.remove_active(chat_id)

async def spam_loop(bot, chat_id, target, task_id, bot_index):
    patterns = [
        "ᚔ᚜ 𓆩『𓍼ֶָ֢˖ ࣪ꨄ𝐃⃝𝛆‌֟፝𝛎 .་༘࿐』𓆪 ᚛ᚔ {name} ON TOP 🔥",
        "OYE {name} TERI MAA KI CHUT ME FIRE 🚀",
        "{name} SYSTEM HANG KAR DIYA DEV BSF ⚡",
        "MASTERY LEVEL OVERLOAD FOR {name} 👑"
    ]
    db.save_active(chat_id, target, "spam")
    i = 0
    
    try:
        while True:
            if controller.should_stop(chat_id, task_id):
                break
            
            await asyncio.sleep(bot_index * 0.15)
            
            msg = patterns[i % len(patterns)].format(name=target)
            try:
                await bot.send_message(chat_id, msg)
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except Exception:
                pass
            
            i += 1
            await asyncio.sleep(controller.speed)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass
    finally:
        db.remove_active(chat_id)

# ==================== COMMANDS ====================
def admin_only(func):
    async def wrapper(update, context):
        try:
            if controller.master is None:
                controller.master = update.effective_user.id
                db.save_setting("master", controller.master)
                controller.admins.add(controller.master)
                db.save_admin(controller.master)
            
            if not controller.is_admin(update.effective_user.id):
                await update.message.reply_text("❌ Access Denied - Admin Rights Required")
                return
            return await func(update, context)
        except Exception as e:
            logger.error(f"Admin check error: {e}")
    return wrapper

@admin_only
async def start_cmd(update, context):
    await update.message.reply_text(
        f"ᚔ᚜ 𓆩『𓍼ֶָ֢˖ ࣪ꨄ𝐃⃝𝛆‌֟፝𝛎 .་༘࿐』𓆪 ᚛ᚔ\n"
        f"┌──『 𓍼ֶָ֢˖ 𝐏ʀᴏꜰɪʟᴇ ˖ֶָ֢𓍼』 ──┐\n"
        f"│ ̼͙̼͙̈́͆̈́ͯ̒̆̀̓ͧ̈́͆̈́ͯ̒̆̀̓ͧ͠͠ᯓ   𝐌ᴀꜱᴛᴇʀ :: 𝐀ᴅᴍɪɴ \n\n"
        f"🚀 **DEV CLUSTER ONLINE** ({len(controller.bots)} Bots Active)\n"
        f"⚡ Speed: {controller.speed}s\n"
        f"🛡️ Anti-Flood Matrix: Enabled\n"
        f"🌐 Keep-Alive Server: Running on Port 8080\n\n"
        f"📌 **Command Center:**\n"
        f"/nc <text> - Smart Rotational Name Change\n"
        f"/spam <text> - High-Speed Multi-Bot Spam\n"
        f"/stop - Halt Current Chat\n"
        f"/stopall - Halt All Operations\n"
        f"/speed <seconds> - Adjust Engine Speed\n"
        f"/stats - Cluster Status"
    )

@admin_only
async def nc_cmd(update, context):
    if not context.args:
        await update.message.reply_text("💡 Usage: `/nc <text>`", parse_mode="Markdown")
        return
    
    target = ' '.join(context.args)
    chat_id = update.effective_chat.id
    
    controller.stop_chat(chat_id)
    controller.attacks[chat_id] = {}
    if chat_id not in controller.stop_flags:
        controller.stop_flags[chat_id] = {}
    
    total_bots = len(controller.bots)
    for idx, bot_info in enumerate(controller.bots):
        task_id = f"{bot_info['id']}_{int(time.time())}_{idx}"
        controller.stop_flags[chat_id][task_id] = False
        task = asyncio.create_task(nc_loop(bot_info['bot'], chat_id, target, task_id, idx, total_bots))
        controller.attacks[chat_id][task_id] = task
    
    await update.message.reply_text(f"✅ NC Attack Deployed: `{target}`", parse_mode="Markdown")

@admin_only
async def spam_cmd(update, context):
    if not context.args:
        await update.message.reply_text("💡 Usage: `/spam <text>`", parse_mode="Markdown")
        return
    
    target = ' '.join(context.args)
    chat_id = update.effective_chat.id
    
    controller.stop_chat(chat_id)
    controller.attacks[chat_id] = {}
    if chat_id not in controller.stop_flags:
        controller.stop_flags[chat_id] = {}
    
    total_bots = len(controller.bots)
    for idx, bot_info in enumerate(controller.bots):
        task_id = f"{bot_info['id']}_{int(time.time())}_{idx}"
        controller.stop_flags[chat_id][task_id] = False
        task = asyncio.create_task(spam_loop(bot_info['bot'], chat_id, target, task_id, idx))
        controller.attacks[chat_id][task_id] = task
    
    await update.message.reply_text(f"✅ Spam Cluster Started: `{target}`", parse_mode="Markdown")

@admin_only
async def stop_cmd(update, context):
    chat_id = update.effective_chat.id
    controller.stop_chat(chat_id)
    await update.message.reply_text("🛑 Operations halted for this chat.")

@admin_only
async def stopall_cmd(update, context):
    controller.stop_all()
    await update.message.reply_text("🛑 All background tasks terminated cluster-wide.")

@admin_only
async def speed_cmd(update, context):
    if not context.args:
        return await update.message.reply_text(f"⚡ Current Engine Speed: {controller.speed}s")
    try:
        speed = float(context.args[0])
        controller.speed = speed
        db.save_setting("speed", speed)
        await update.message.reply_text(f"✅ Speed Updated: {speed}s")
    except:
        await update.message.reply_text("❌ Invalid speed format.")

@admin_only
async def stats_cmd(update, context):
    active = db.get_active()
    await update.message.reply_text(
        f"📊 **Cluster Metrics:**\n"
        f"🤖 Active Bots: {len(controller.bots)}/9\n"
        f"⚡ Delay: {controller.speed}s\n"
        f"🔥 Active Operations: {len(active)}",
        parse_mode="Markdown"
    )

# ==================== RESTORE ====================
async def restore_attacks():
    active = db.get_active()
    if not active:
        return
    
    logger.info(f"🔄 Restoring {len(active)} operations...")
    total_bots = len(controller.bots)
    
    for chat_id, target, attack_type in active:
        controller.attacks[chat_id] = {}
        if chat_id not in controller.stop_flags:
            controller.stop_flags[chat_id] = {}
        
        for idx, bot_info in enumerate(controller.bots):
            task_id = f"{bot_info['id']}_restore_{int(time.time())}_{idx}"
            controller.stop_flags[chat_id][task_id] = False
            
            if attack_type == "nc":
                task = asyncio.create_task(nc_loop(bot_info['bot'], chat_id, target, task_id, idx, total_bots))
            else:
                task = asyncio.create_task(spam_loop(bot_info['bot'], chat_id, target, task_id, idx))
            
            controller.attacks[chat_id][task_id] = task

# ==================== MAIN ====================
async def main():
    print("=" * 60)
    print("ᚔ᚜ 𓆩『𓍼ֶָ֢˖ ࣪ꨄ𝐃⃝𝛆‌֟፝𝛎 .་༘࿐』𓆪 ᚛ᚔ - CLUSTER BOOTING")
    print("=" * 60)
    
    valid_tokens = [t.strip() for t in TOKENS if t.strip() and len(t) > 10]
    
    for idx, token in enumerate(valid_tokens):
        try:
            app = Application.builder().token(token).build()
            bot_info = await asyncio.wait_for(app.bot.get_me(), timeout=10)
            
            app.add_handler(CommandHandler("start", start_cmd))
            app.add_handler(CommandHandler("nc", nc_cmd))
            app.add_handler(CommandHandler("spam", spam_cmd))
            app.add_handler(CommandHandler("stop", stop_cmd))
            app.add_handler(CommandHandler("stopall", stopall_cmd))
            app.add_handler(CommandHandler("speed", speed_cmd))
            app.add_handler(CommandHandler("stats", stats_cmd))
            
            await app.initialize()
            await app.start()
            if app.updater:
                await app.updater.start_polling()
            
            controller.bots.append({'id': bot_info.id, 'username': bot_info.username, 'bot': app.bot, 'app': app})
            print(f"✅ Bot #{idx+1} Online: @{bot_info.username}")
            
        except Exception as e:
            print(f"❌ Bot #{idx+1} Failed: {str(e)[:30]}")
    
    print("=" * 60)
    print(f"🚀 Cluster Ready: {len(controller.bots)} / 9 Bots Operational")
    print("=" * 60)
    
    await restore_attacks()
    
    while True:
        await asyncio.sleep(60)

# ==================== SIGNAL HANDLER ====================
def signal_handler(sig, frame):
    print("\n🛑 Shutting down cluster gracefully...")
    controller.stop_all()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    # Start Keep-Alive Server
    keep_alive()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Stopped")
        controller.stop_all()
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
