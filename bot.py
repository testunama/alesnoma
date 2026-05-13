#!/usr/bin/env python3
import asyncio, sys, os
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from database import Database
from config import API_ID, API_HASH, BOT_TOKEN, PORT, ADMIN_IDS
from utils import Scheduler
from force_check import check_force_join

# Flask for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Running!"

@app.route('/health')
def health():
    return "OK", 200

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
from callbacks_b import user_states

# Register callbacks
@client.on_callback_query()
async def callback_handler(client, c: CallbackQuery):
    if not await check_force_join(client, c):
        return
    
    data = c.data
    
    # User callbacks
    if data == 'profile':
        await profile_cb(client, c)
    elif data == 'my_monitors':
        await my_monitors_cb(client, c)
    elif data.startswith('detail_'):
        await monitor_detail_cb(client, c)
    elif data.startswith('refresh_'):
        await refresh_cb(client, c)
    elif data.startswith('toggle_'):
        await toggle_cb(client, c)
    elif data.startswith('delete_'):
        await delete_cb(client, c)
    elif data.startswith('confirmdel_'):
        await confirm_del_cb(client, c)
    elif data == 'main_menu':
        await main_menu_cb(client, c)
    
    # Payment callbacks
    elif data == 'premium_menu':
        await premium_menu_cb(client, c)
    elif data.startswith('buy_'):
        await select_method_cb(client, c)
    elif data == 'pay_upi':
        await pay_upi_cb(client, c)
    elif data == 'pay_bank':
        await pay_bank_cb(client, c)
    
    # Admin callbacks
    elif data == 'admin_panel':
        await admin_panel_cb(client, c)
    elif data == 'admin_users':
        await admin_users_cb(client, c)
    elif data.startswith('user_'):
        await user_detail_cb(client, c)
    elif data.startswith('ban_'):
        await ban_cb(client, c)
    elif data.startswith('setprem_'):
        await set_premium_cb(client, c)
    elif data == 'verify_payments':
        await verify_payments_cb(client, c)
    elif data.startswith('verify_'):
        await verify_payment_cb(client, c)
    elif data.startswith('reject_'):
        await reject_cb(client, c)
    elif data == 'admin_stats':
        await admin_stats_cb(client, c)
    elif data == 'export_all':
        await export_all_cb(client, c)
    elif data.startswith('exportusr_'):
        uid = int(data.replace('exportusr_', ''))
        text = await db.generate_file(uid)
        filename = f"user_{uid}.txt"
        with open(filename, 'w') as f: f.write(text)
        await client.send_document(c.from_user.id, filename)
        await c.answer("Exported!")
    elif data == 'edit_contact':
        await edit_contact_cb(client, c)
    elif data == 'check_fj':
        from force_check import check_force_join_callback
        await check_force_join_callback(client, c)
    elif data == 'add_monitor':
        limit = await db.get_monitor_limit(c.from_user.id)
        user = await db.get_user(c.from_user.id)
        if user and user['monitor_count'] >= limit:
            await c.edit_message_text(f"❌ Limit reached ({limit})!", reply_markup=back_button("main_menu"))
        else:
            user_states[c.from_user.id] = {'waiting': 'add_url'}
            await c.edit_message_text("🔗 Send URL:\nExample: https://google.com\n/cancel to abort")
    
    elif data.startswith('admin_plans'):
        await admin_plans_cb(client, c)
    elif data.startswith('plan_'):
        await plan_detail_cb(client, c)
    elif data.startswith('delplan_'):
        await delete_plan_cb(client, c)
    elif data.startswith('toggleplan_'):
        await toggle_plan_cb(client, c)
    elif data == 'edit_methods':
        await edit_methods_cb(client, c)
    elif data.startswith('edit_upi'):
        await edit_upi_cb(client, c)
    elif data.startswith('edit_paypal'):
        await edit_paypal_cb(client, c)
    elif data.startswith('edit_bank'):
        await edit_bank_cb(client, c)
    elif data.startswith('add_plan'):
        await add_plan_cb(client, c)
    elif data == 'fj_menu':
        await fj_menu_cb(client, c)
    elif data == 'fj_toggle':
        await fj_toggle_cb(client, c)
    elif data.startswith('fj_remove_'):
        cid = int(data.replace('fj_remove_', ''))
        await db.remove_fj_channel(cid)
        await fj_menu_cb(client, c)
    elif data == 'fj_add':
        admin_states[c.from_user.id] = {'action': 'fj_add'}
        await c.edit_message_text("📢 Send channel ID or @username\nExample: -1001234567890 or @channel")
    elif data == 'broadcast':
        admin_states[c.from_user.id] = {'action': 'broadcast'}
        await c.edit_message_text("📨 Send message to broadcast to all users:")
    
    await c.answer()

# Handle admin messages
from callbacks_c import admin_states, handle_admin_msg

@client.on_message(filters.private & filters.user(ADMIN_IDS) & filters.text)
async def on_admin_text(client, message):
    uid = message.from_user.id
    
    # Check if admin is in a state
    if uid in admin_states:
        action = admin_states[uid].get('action')
        
        if action == 'fj_add':
            text = message.text.strip()
            chat_info = None
            
            try:
                # Try as ID
                try:
                    chat_id = int(text)
                    chat = await client.get_chat(chat_id)
                    chat_info = {
                        'id': chat.id,
                        'username': chat.username or '',
                        'name': chat.title or str(chat.id),
                        'type': str(chat.type),
                        'invite_link': getattr(chat, 'invite_link', '') or ''
                    }
                except:
                    # Try as username
                    if text.startswith('@'): text = text[1:]
                    chat = await client.get_chat(f"@{text}")
                    chat_info = {
                        'id': chat.id,
                        'username': chat.username or text,
                        'name': chat.title or text,
                        'type': str(chat.type),
                        'invite_link': chat.invite_link or f"https://t.me/{chat.username}"
                    }
                
                if chat_info:
                    ok = await db.add_fj_channel(chat_info)
                    await message.reply_text(f"✅ Added: {chat_info['name']}" if ok else "❌ Already exists!")
                else:
                    await message.reply_text("❌ Could not get chat info!")
                
            except Exception as e:
                await message.reply_text(f"❌ Error: {e}\nSend valid ID or @username")
            
            admin_states.pop(uid, None)
            return
        
        elif action == 'broadcast':
            users = await db.get_all_users()
            sent = 0
            for u in users:
                try:
                    await message.copy(u['user_id'])
                    sent += 1
                except: pass
            
            await message.reply(f"📨 Sent to {sent}/{len(users)}")
            admin_states.pop(uid, None)
            return
        
        else:
            await handle_admin_msg(client, message)
            return
    
    # Check for add monitor flow for admins too
    if uid in user_states and user_states[uid].get('waiting') == 'add_url':
        return await handle_add_url(client, message)
    elif uid in user_states and user_states[uid].get('waiting') == 'add_name':
        return await handle_add_name(client, message)
    
    # If no state, pass to handle_admin_msg for other admin actions
    await handle_admin_msg(client, message)

# Handle add monitor URL/Name for users
async def handle_add_url(client, message):
    uid = message.from_user.id
    url = message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        return await message.reply("❌ Invalid URL! Use http:// or https://")
    
    dup = await db.check_duplicate(uid, url)
    if dup:
        return await message.reply("❌ Already monitoring!")
    
    user_states[uid]['url'] = url
    user_states[uid]['waiting'] = 'add_name'
    await message.reply("✅ Send name for this monitor:")

async def handle_add_name(client, message):
    uid = message.from_user.id
    name = message.text.strip()
    url = user_states[uid].get('url')
    
    if not url:
        return
    
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

@client.on_message(filters.private & filters.text & ~filters.command(['start', 'help', 'menu', 'adminhelp', 'add', 'remove', 'ban', 'unban', 'users', 'user', 'upi', 'paypal', 'bank', 'plans', 'addplan', 'delplan', 'toggleplan', 'pending', 'verify', 'reject', 'fjadd', 'fjremove', 'fjlist', 'fjtoggle', 'stats', 'export', 'exportuser', 'broadcast', 'tierview', 'tierset', 'contact']))
async def on_user_text(client, message):
    uid = message.from_user.id
    
    if uid in ADMIN_IDS:
        return  # Admin messages handled separately
    
    if not await check_force_join(client, message):
        return
    
    if uid in user_states:
        if user_states[uid].get('waiting') == 'add_url':
            await handle_add_url(client, message)
        elif user_states[uid].get('waiting') == 'add_name':
            await handle_add_name(client, message)

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
