#!/usr/bin/env python3
import asyncio, sys, os
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from database import Database
from config import API_ID, API_HASH, BOT_TOKEN, PORT
from utils import Scheduler
from force_check import check_force_join

# Flask for Render
app = Flask(__name__)
@app.route('/'): return "Bot Running!"
@app.route('/health'): return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False)

# Pyrogram Client
client = Client("uptime_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database
db = Database()

# Import all handlers
import handlers_user
import handlers_payment
import admin_commands
import admin_force

# Import callbacks
from callbacks_a import *
from callbacks_b import *
from callbacks_c import *

# Register callbacks
@client.on_callback_query()
async def callback_handler(client, c: CallbackQuery):
    if not await check_force_join(client, c):
        return
    
    data = c.data
    
    # User callbacks
    if data == 'profile': await profile_cb(client, c)
    elif data == 'my_monitors': await my_monitors_cb(client, c)
    elif data.startswith('detail_'): await monitor_detail_cb(client, c)
    elif data.startswith('refresh_'): await refresh_cb(client, c)
    elif data.startswith('toggle_'): await toggle_cb(client, c)
    elif data.startswith('delete_'): await delete_cb(client, c)
    elif data.startswith('confirmdel_'): await confirm_del_cb(client, c)
    elif data == 'main_menu': await main_menu_cb(client, c)
    
    # Payment callbacks
    elif data == 'premium_menu': await premium_menu_cb(client, c)
    elif data.startswith('buy_'): await select_method_cb(client, c)
    elif data == 'pay_upi': await pay_upi_cb(client, c)
    elif data == 'pay_bank': await pay_bank_cb(client, c)
    
    # Admin callbacks
    elif data == 'admin_panel': await admin_panel_cb(client, c)
    elif data == 'admin_users': await admin_users_cb(client, c)
    elif data.startswith('user_'): await user_detail_cb(client, c)
    elif data.startswith('ban_'): await ban_cb(client, c)
    elif data.startswith('setprem_'): await set_premium_cb(client, c)
    elif data == 'verify_payments': await verify_payments_cb(client, c)
    elif data.startswith('verify_'): await verify_payment_cb(client, c)
    elif data.startswith('reject_'): await reject_cb(client, c)
    elif data == 'admin_stats': await admin_stats_cb(client, c)
    elif data == 'export_all': await export_all_cb(client, c)
    elif data.startswith('exportusr_'): 
        from callbacks_c import admin_states
        # use the existing one
    elif data == 'edit_contact': await edit_contact_cb(client, c)
    elif data == 'check_fj': await check_force_join(client, c)
    elif data == 'add_monitor':
        # Handle add monitor
        from callbacks_b import user_states
        user_states[c.from_user.id] = {'waiting': 'add_url'}
        await c.edit_message_text("🔗 Send URL:\nExample: https://google.com")
    
    c.answer()

# Handle admin messages
from callbacks_c import handle_admin_msg
@client.on_message(filters.private & filters.text & ~filters.command(['start', 'help', 'menu', 'adminhelp', 'add', 'remove', 'ban', 'unban', 'users', 'user', 'upi', 'paypal', 'bank', 'plans', 'addplan', 'delplan', 'toggleplan', 'pending', 'verify', 'reject', 'fjadd', 'fjremove', 'fjlist', 'fjtoggle', 'stats', 'export', 'exportuser', 'broadcast', 'tierview', 'tierset', 'contact']))
async def on_admin_text(client, message):
    await handle_admin_msg(client, message)

# Handle add monitor URL/Name
from callbacks_b import user_states
@client.on_message(filters.private & filters.text & ~filters.command(['start', 'help', 'menu']))
async def on_text(client, message):
    uid = message.from_user.id
    
    if uid in user_states and user_states[uid].get('waiting') == 'add_url':
        url = message.text.strip()
        if not url.startswith(('http://', 'https://')):
            return await message.reply("❌ Invalid URL!")
        
        dup = await db.check_duplicate(uid, url)
        if dup: return await message.reply("❌ Already monitoring!")
        
        user_states[uid]['url'] = url
        user_states[uid]['waiting'] = 'add_name'
        await message.reply("✅ Send name for this monitor:")
    
    elif uid in user_states and user_states[uid].get('waiting') == 'add_name':
        name = message.text.strip()
        url = user_states[uid].get('url')
        if not url: return
        
        limit = await db.get_monitor_limit(uid)
        user = await db.get_user(uid)
        if user['monitor_count'] >= limit:
            return await message.reply(f"❌ Limit reached ({limit})!")
        
        interval = await db.get_monitor_duration(uid)
        await db.create_monitor(uid, url, name, interval)
        await db.inc_monitors(uid)
        
        from keyboards_a import back_button
        await message.reply(f"✅ Added!\n\n{name}\n{url}\n⏱ {interval}min", reply_markup=back_button("my_monitors"))
        user_states.pop(uid, None)

# Start bot
async def main():
    await db.connect()
    await client.start()
    
    # Start scheduler
    s = Scheduler(db, client)
    s.start()
    
    print("✅ Bot Running!")
    await asyncio.get_event_loop().create_future()

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
