from pyrogram import Client
from pyrogram.types import CallbackQuery
from datetime import datetime
from database import Database
from keyboards_a import *
from config import ADMIN_IDS

db = Database()

async def profile_cb(client, cb: CallbackQuery):
    u = await db.get_user(cb.from_user.id)
    if not u: return
    premium = "❌ Free"
    if u.get('is_premium') and u.get('premium_expiry') and u['premium_expiry'] > datetime.now():
        days = (u['premium_expiry'] - datetime.now()).days
        premium = f"💎 {u.get('premium_plan', 'Premium')} ({days}d)"
    limit = await db.get_monitor_limit(u['user_id'])
    dur = await db.get_monitor_duration(u['user_id'])
    text = f"👤 Profile\n\nID: {u['user_id']}\nPremium: {premium}\nMonitors: {u['monitor_count']}/{limit}\nInterval: {dur}min"
    await cb.edit_message_text(text, reply_markup=back_button("main_menu"))

async def my_monitors_cb(client, cb: CallbackQuery):
    monitors = await db.get_user_monitors(cb.from_user.id)
    if not monitors: await cb.edit_message_text("No monitors!", reply_markup=back_button("main_menu")); return
    text = "📊 Your Monitors\n\n"
    kb = []
    for m in monitors[:15]:
        emoji = "🟢" if m['status'] == 'up' else "🔴"
        text += f"{emoji} {m['name']} - {m['uptime_percentage']}%\n"
        kb.append([InlineKeyboardButton(f"{emoji} {m['name'][:30]}", callback_data=f"detail_{m['monitor_id']}")])
    kb.append([InlineKeyboardButton("➕ Add", callback_data="add_monitor")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    await cb.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def monitor_detail_cb(client, cb: CallbackQuery):
    mid = cb.data.replace("detail_", "")
    m = await db.get_monitor(mid)
    if not m or m['user_id'] != cb.from_user.id: return await cb.answer("Not found!")
    emoji = "🟢" if m['status'] == 'up' else "🔴"
    text = f"{emoji} {m['name']}\n🔗 {m['url']}\n⏱ {m['check_interval']}min\n📊 {m['uptime_percentage']}%\n✅{m['successful_checks']} ❌{m['failed_checks']}"
    await cb.edit_message_text(text, reply_markup=monitor_actions(mid))

async def refresh_cb(client, cb: CallbackQuery):
    mid = cb.data.replace("refresh_", "")
    m = await db.get_monitor(mid)
    if m and m['user_id'] == cb.from_user.id:
        from utils import check_website
        r = await check_website(m['url'])
        await db.update_monitor_status(mid, r['status'], r.get('time', 0))
    await monitor_detail_cb(client, cb)

async def toggle_cb(client, cb: CallbackQuery):
    mid = cb.data.replace("toggle_", "")
    m = await db.get_monitor(mid)
    if m and m['user_id'] == cb.from_user.id:
        await db.toggle_monitor(mid, not m['is_active'])
        await cb.answer(f"{'Activated' if not m['is_active'] else 'Paused'}!")
    await monitor_detail_cb(client, cb)

async def delete_cb(client, cb: CallbackQuery):
    mid = cb.data.replace("delete_", "")
    m = await db.get_monitor(mid)
    if m and m['user_id'] == cb.from_user.id:
        await cb.edit_message_text(f"⚠️ Delete {m['name']}?", reply_markup=confirm_delete(mid))

async def confirm_del_cb(client, cb: CallbackQuery):
    mid = cb.data.replace("confirmdel_", "")
    m = await db.get_monitor(mid)
    if m and m['user_id'] == cb.from_user.id:
        await db.delete_monitor(mid)
        await db.dec_monitors(cb.from_user.id)
    await my_monitors_cb(client, cb)

async def main_menu_cb(client, cb: CallbackQuery):
    contact = await db.get_contact()
    await cb.edit_message_text("🏠 Menu", reply_markup=await main_menu(cb.from_user.id, ADMIN_IDS, contact))
