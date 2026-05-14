#!/usr/bin/env python3
import asyncio, sys, os, logging
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
from database import Database
from config import API_ID, API_HASH, BOT_TOKEN, PORT, ADMIN_IDS
from utils import Scheduler
from force_check import check_force_join

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info(f"API_ID={API_ID}, PORT={PORT}")

# Flask
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Running!"
@app.route('/health')
def health(): return "OK", 200

# Pyrogram Client (Default workers)
client = Client(
    name=":memory:",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

db = Database()

# ============ IMPORTS ============
import handlers_user
import handlers_payment
import admin_commands
import admin_force

from callbacks_a import *
from callbacks_b import *
from callbacks_c import *
from callbacks_b import user_states
from callbacks_c import admin_states, handle_admin_msg

# ============ CALLBACK ROUTER ============
@client.on_callback_query()
async def on_callback(client, cb: CallbackQuery):
    data = cb.data
    uid = cb.from_user.id
    
    if not await check_force_join(client, cb):
        return
    
    if data == 'profile': await profile_cb(client, cb)
    elif data == 'my_monitors': await my_monitors_cb(client, cb)
    elif data == 'main_menu': await main_menu_cb(client, cb)
    elif data == 'premium_menu': await premium_menu_cb(client, cb)
    elif data == 'add_monitor':
        limit = await db.get_monitor_limit(uid)
        user = await db.get_user(uid)
        if user and user['monitor_count'] >= limit:
            from keyboards_a import back_button
            await cb.edit_message_text(f"❌ Limit: {limit}", reply_markup=back_button("main_menu"))
        else:
            user_states[uid] = {'waiting': 'add_url'}
            await cb.edit_message_text("🔗 Send URL:")
    
    elif data.startswith('detail_'): await monitor_detail_cb(client, cb)
    elif data.startswith('refresh_'): await refresh_cb(client, cb)
    elif data.startswith('toggle_'): await toggle_cb(client, cb)
    elif data.startswith('delete_'): await delete_cb(client, cb)
    elif data.startswith('confirmdel_'): await confirm_del_cb(client, cb)
    elif data.startswith('buy_'): await select_method_cb(client, cb)
    elif data == 'pay_upi': await pay_upi_cb(client, cb)
    elif data == 'pay_bank': await pay_bank_cb(client, cb)
    
    elif data == 'admin_panel': await admin_panel_cb(client, cb)
    elif data == 'admin_users': await admin_users_cb(client, cb)
    elif data.startswith('user_'): await user_detail_cb(client, cb)
    elif data.startswith('ban_'): await ban_cb(client, cb)
    elif data.startswith('setprem_'): await set_premium_cb(client, cb)
    elif data == 'verify_payments': await verify_payments_cb(client, cb)
    elif data.startswith('verify_'): await verify_payment_cb(client, cb)
    elif data.startswith('reject_'): await reject_cb(client, cb)
    elif data == 'edit_contact': await edit_contact_cb(client, cb)
    elif data == 'admin_stats': await admin_stats_cb(client, cb)
    elif data == 'export_all': await export_all_cb(client, cb)
    elif data.startswith('exportusr_'):
        uid2 = int(data.replace('exportusr_', ''))
        txt = await db.generate_file(uid2)
        fn = f"user_{uid2}.txt"
        with open(fn, 'w') as f: f.write(txt)
        await client.send_document(uid, fn)
    
    elif data == 'admin_plans': await admin_plans_cb(client, cb)
    elif data.startswith('plan_'): await plan_detail_cb(client, cb)
    elif data.startswith('delplan_'): await delete_plan_cb(client, cb)
    elif data.startswith('toggleplan_'): await toggle_plan_cb(client, cb)
    elif data == 'edit_methods': await edit_methods_cb(client, cb)
    
    elif data == 'fj_menu': await fj_menu_cb(client, cb)
    elif data == 'fj_toggle': await fj_toggle_cb(client, cb)
    elif data.startswith('fj_remove_'):
        await db.remove_fj_channel(int(data.replace('fj_remove_', '')))
        await fj_menu_cb(client, cb)
    elif data == 'fj_add':
        admin_states[uid] = {'action': 'fj_add'}
        await cb.edit_message_text("📢 Send channel ID or @username:")
    elif data == 'broadcast':
        admin_states[uid] = {'action': 'broadcast'}
        await cb.edit_message_text("📨 Send message:")
    elif data == 'check_fj':
        from force_check import check_force_join_callback
        await check_force_join_callback(client, cb)
    
    await cb.answer()

# ============ MESSAGE HANDLER ============
@client.on_message(filters.text & filters.private)
async def on_message(client, msg: Message):
    uid = msg.from_user.id
    txt = msg.text or ""
    if txt.startswith('/'): return
    
    if uid not in ADMIN_IDS:
        if not await check_force_join(client, msg):
            return
    
    if uid in admin_states:
        action = admin_states[uid].get('action')
        if action == 'fj_add':
            try:
                t = txt.strip().replace('@', '')
                try: chat = await client.get_chat(int(t))
                except: chat = await client.get_chat(f"@{t}")
                info = {'id': chat.id, 'username': chat.username or '', 'name': chat.title or t, 'type': str(chat.type), 'invite_link': getattr(chat, 'invite_link', '') or ''}
                ok = await db.add_fj_channel(info)
                await msg.reply(f"✅ {info['name']}" if ok else "❌ Already exists!")
            except Exception as e:
                await msg.reply(f"❌ Error: {e}")
            admin_states.pop(uid, None)
            return
        elif action == 'broadcast':
            users = await db.get_all_users()
            s = 0
            for u in users:
                try: await msg.copy(u['user_id']); s += 1
                except: pass
            await msg.reply(f"📨 {s}/{len(users)}")
            admin_states.pop(uid, None)
            return
        else:
            await handle_admin_msg(client, msg)
            return
    
    if uid in user_states:
        state = user_states[uid].get('waiting')
        if state == 'add_url':
            url = txt.strip()
            if not url.startswith(('http://', 'https://')):
                return await msg.reply("❌ Invalid URL!")
            if await db.check_duplicate(uid, url):
                return await msg.reply("❌ Already monitoring!")
            user_states[uid]['url'] = url
            user_states[uid]['waiting'] = 'add_name'
            await msg.reply("✅ Send name:")
            return
        elif state == 'add_name':
            name = txt.strip()
            url = user_states[uid].get('url')
            limit = await db.get_monitor_limit(uid)
            user = await db.get_user(uid)
            if user and user['monitor_count'] >= limit:
                return await msg.reply(f"❌ Limit: {limit}!")
            interval = await db.get_monitor_duration(uid)
            await db.create_monitor(uid, url, name, interval)
            await db.inc_monitors(uid)
            from keyboards_a import back_button
            await msg.reply(f"✅ {name}\n{url}\n⏱{interval}min", reply_markup=back_button("my_monitors"))
            user_states.pop(uid, None)
            return
    
    if uid in ADMIN_IDS:
        await handle_admin_msg(client, msg)

# ============ MAIN ============
async def main():
    logger.info("Connecting DB...")
    await db.connect()
    
    logger.info("Starting Pyrogram...")
    await client.start()
    me = await client.get_me()
    logger.info(f"✅ Bot @{me.username} LIVE!")
    
    Scheduler(db, client).start()
    logger.info("✅ Scheduler started!")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False), daemon=True).start()
    asyncio.run(main())
