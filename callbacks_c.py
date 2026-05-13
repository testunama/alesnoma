from pyrogram import Client
from pyrogram.types import CallbackQuery, Message
from datetime import datetime
from database import Database
from keyboards_a import *
from keyboards_b import *
from config import ADMIN_IDS

db = Database()
admin_states = {}

async def admin_panel_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    await cb.edit_message_text("⚙️ Admin", reply_markup=admin_panel())

async def admin_users_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    users = await db.get_all_users()
    await cb.edit_message_text("👥 Users", reply_markup=users_list(users))

async def user_detail_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    uid = int(cb.data.replace("user_", ""))
    u = await db.get_user(uid)
    if not u: return
    text = f"👤 {u['first_name']}\nID: {uid}\nPremium: {u.get('is_premium')}\nBanned: {u.get('is_banned')}"
    await cb.edit_message_text(text, reply_markup=user_actions(uid, u.get('is_banned', False)))

async def ban_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    uid = int(cb.data.replace("ban_", ""))
    u = await db.get_user(uid)
    await db.ban_user(uid, not u.get('is_banned'))
    await cb.answer("Done!")
    await user_detail_cb(client, cb)

async def set_premium_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    uid = int(cb.data.replace("setprem_", ""))
    admin_states[cb.from_user.id] = {'action': 'set_premium', 'uid': uid}
    await cb.edit_message_text("Send: days [monitor_limit] [check_interval]\nExample: 30 50 1")

async def verify_payments_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    pending = await db.get_pending_payments()
    if not pending: return await cb.edit_message_text("✅ None!", reply_markup=back_button("admin_panel"))
    text = "💳 Pending\n\n"
    for p in pending: text += f"🆔 {p['payment_id']}\n👤{p['user_id']} 💰{p['amount']}\n\n"
    await cb.edit_message_text(text, reply_markup=pending_kb(pending))

async def verify_payment_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    pid = cb.data.replace("verify_", "")
    p = await db.get_payment(pid)
    if p:
        await db.verify_payment(pid, cb.from_user.id)
        plan = await db.get_plan(p['plan_id'])
        if plan: await db.set_premium(p['user_id'], plan['duration_days'], plan['name'], plan.get('monitor_limit', 0), plan.get('check_interval', 0))
        try: await client.send_message(p['user_id'], "✅ Verified!")
        except: pass
    await verify_payments_cb(client, cb)

async def reject_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    pid = cb.data.replace("reject_", "")
    admin_states[cb.from_user.id] = {'action': 'reject', 'pid': pid}
    await cb.edit_message_text(f"Reason for {pid}:")

async def edit_contact_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    admin_states[cb.from_user.id] = {'action': 'edit_contact'}
    contact = await db.get_contact()
    await cb.edit_message_text(f"Current: {contact.get('url')}\n\nSend: text | url\nExample: 📞 Support | https://t.me/support")

async def admin_stats_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    us = await db.get_stats()
    monitors = await db.get_all_active_monitors()
    up = sum(1 for m in monitors if m['status'] == 'up')
    pending = await db.get_pending_payments()
    text = f"📊 Stats\n\n👥 {us['total_users']} | 💎{us['premium_users']}\n📊 {len(monitors)} | 🟢{up}\n💳 {len(pending)} pending"
    await cb.edit_message_text(text, reply_markup=back_button("admin_panel"))

async def export_all_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS: return
    text = await db.generate_file()
    with open("export.txt", 'w') as f: f.write(text)
    await client.send_document(cb.from_user.id, "export.txt")
    await cb.answer("Done!")

async def handle_admin_msg(client, message: Message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS or uid not in admin_states: return
    
    state = admin_states[uid]
    action = state.get('action')
    
    if action == 'set_premium':
        parts = message.text.split()
        days = int(parts[0])
        limit = int(parts[1]) if len(parts) > 1 else 0
        interval = int(parts[2]) if len(parts) > 2 else 0
        await db.set_premium(state['uid'], days, "Admin", limit, interval)
        await message.reply_text(f"✅ {days}d | Limit:{limit if limit else 'Default'} | Interval:{interval if interval else 'Default'}min")
        admin_states.pop(uid)
    
    elif action == 'reject':
        p = await db.get_payment(state['pid'])
        if p:
            await db.reject_payment(state['pid'], uid, message.text)
            try: await client.send_message(p['user_id'], f"❌ Rejected: {message.text}")
            except: pass
        await message.reply_text("✅ Rejected!")
        admin_states.pop(uid)
    
    elif action == 'edit_contact':
        parts = message.text.split('|')
        if len(parts) >= 2:
            await db.update_contact({'text': parts[0].strip(), 'url': parts[1].strip()})
        else:
            await db.update_contact({'url': message.text.strip()})
        await message.reply_text("✅ Contact updated!")
        admin_states.pop(uid)
