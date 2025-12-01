import sys
import glob
import importlib
from pathlib import Path
from pyrogram import Client, idle, __version__
from pyrogram.raw.all import layer
import time
import asyncio
from datetime import date, datetime
import pytz
from aiohttp import web
from database.ia_filterdb import Media, Media2
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script
from plugins import web_server, check_expired_premium 
from Lucia.Bot import SilentX
from Lucia.util.keepalive import ping_server
from Lucia.Bot.clients import initialize_clients
import pyrogram.utils
from PIL import Image
import threading, requests
from logging_helper import LOGGER

botStartTime = time.time()
ppath = "plugins/*.py"
files = glob.glob(ppath)

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

# ---------------------- PING LOOP ----------------------
# Put your actual Render URL here
import requests
import threading
from logging_helper import LOGGER
URL = "https://some-auto-filter.onrender.com"

def ping_loop():
    while True:
        try:
            r = requests.get(URL, timeout=10)
            if r.status_code == 200:
                LOGGER.info("✅ Ping Successful")
            else:
                LOGGER.warning(f"⚠️ Ping Failed: {r.status_code}")
        except Exception as e:
            LOGGER.error(f"❌ Exception During Ping: {e}")
        # wait 2 minutes before next ping
        time.sleep(120)

# Start the ping loop in a separate thread
threading.Thread(target=ping_loop, daemon=True).start()

# ------------------- BOT START ------------------------
async def SilentXBotz_start():
    LOGGER.info('Initializing Your Bot!')
    
    # Start main bot client
    await SilentX.start()
    bot_info = await SilentX.get_me()
    SilentX.username = bot_info.username

    # Initialize additional clients
    await initialize_clients()

    # ---------------- PLUGINS IMPORT -------------------
    for name in files:
        try:
            patt = Path(name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = f"plugins.{plugin_name}"
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            LOGGER.info("Import Plugins - " + plugin_name)
        except Exception as e:
            LOGGER.error(f"❌ Failed to import plugin {plugin_name}: {e}")

    # Keepalive on Heroku
    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # ------------------- DATABASE ----------------------
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats
    await Media.ensure_indexes()
    if MULTIPLE_DB:
        await Media2.ensure_indexes()
        LOGGER.info("Multiple Database Mode On. Files will save in second DB if first is full")
    else:
        LOGGER.info("Single DB Mode On! Files will save in first database")

    # ------------------- BOT INFO ----------------------
    me = await SilentX.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention
    SilentX.username = '@' + me.username

    # Schedule premium check
    SilentX.loop.create_task(check_expired_premium(SilentX))

    LOGGER.info(f"{me.first_name} with Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
    LOGGER.info(script.LOGO)

    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    current_time = now.strftime("%H:%M:%S %p")  # Avoid shadowing 'time'

    # Notify log channel
    await SilentX.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(temp.B_LINK, today, current_time))
    try:
        for admin in ADMINS:
            await SilentX.send_message(chat_id=admin, text=f"<b>๏[-ิ_•ิ]๏ {me.mention} Restarted ✅</code></b>")
    except:
        pass

    # ---------------- WEB SERVER ----------------------
    app_instance = await web_server()
    if app_instance is None:  # Ensure it's not None
        app_instance = web.Application()

    app = web.AppRunner(app_instance)
    await app.setup()
    await web.TCPSite(app, "0.0.0.0", PORT).start()

    # ---------------- IDLE ----------------------------
    await idle()

# -------------------- MAIN ---------------------------
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(SilentXBotz_start())
    except KeyboardInterrupt:
        LOGGER.info('Service Stopped Bye 👋')
