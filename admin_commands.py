from pyrogram import Client, filters
from pyrogram.types import Message
from database import Database
from config import ADMIN_IDS
from datetime import datetime, timedelta

db = Database()

@Client.on_message(filters.command('adminhelp') & filters.user(ADMIN_IDS))
async def admin_help(client, message: Message):
    text = """
🔐 **Admin Commands**

/add uid days [limit] [interval] - Premium with custom limits
/remove uid - Remove premium
/ban uid - Ban user
/unban uid - Unban
/users - List users
/user uid - User detail
/upi id - Set UPI
/bank acc|ifsc|name - Set bank
/plans - View plans
/addplan name|price|days|currency|limit|interval
/delplan id
/toggleplan id
/contact text|url - Set contact button
/verify pid - Verify payment
/reject pid reason - Reject
/fjadd -id/@username - Add channel
/fjremove id - Remove
/fjlist - List
/fjtoggle - Toggle
/stats - Statistics
/export - Export all
/broadcast - Reply to message
/tierview - View tiers
/tierset free_mon prem_mon free_int prem_int
"""
    await message.reply(text)

@Client.on_message(filters.command('add') & filters.user(ADMIN_IDS))
async def add_cmd(client, message: Message):
    try:
        args = message.text.split()
        if len(args) < 3: return await message.reply("/add uid days [limit] [interval]")
        uid, days = int(args[1]), int(args[2])
        limit = int(args[3]) if len(args) > 3 else 0
        interval = int(args[4]) if len(args) > 4 else 0
        await db.set_premium(uid, days, "Admin", limit, interval)
        await message.reply(f"✅ {uid}: {days}d | Limit:{limit if limit else 'Default'} | Interval:{interval if interval else 'Default'}min")
        try: await client.send_message(uid, f"🎉 Premium {days}d!")
        except: pass
    except Exception as e: await message.reply(f"❌ {e}")

@Client.on_message(filters.command('remove') & filters.user(ADMIN_IDS))
async def remove_cmd(client, message: Message):
    try:
        args = message.text.split()
        if len(args) < 2: return await message.reply("/remove uid")
        await db.remove_premium(int(args[1]))
        await message.reply(f"✅ Removed!")
    except: pass

@Client.on_message(filters.command(['ban', 'unban']) & filters.user(ADMIN_IDS))
async def ban_cmd(client, message: Message):
    try:
        args = message.text.split()
        if len(args) < 2: return await message.reply(f"/{message.command[0]} uid")
        await db.ban_user(int(args[1]), message.command[0] == 'ban')
        await message.reply(f"✅ Done!")
    except: pass

@Client.on_message(filters.command('users') & filters.user(ADMIN_IDS))
async def users_cmd(client, message: Message):
    users = await db.get_all_users()
    s = await db.get_stats()
    text = f"👥 {s['total_users']} | 💎{s['premium_users']} | 🚫{s['banned_users']}\n\n"
    for u in users[:30]: text += f"{u['first_name'][:15]} [{u['user_id']}]\n"
    await message.reply(text)

@Client.on_message(filters.command('contact') & filters.user(ADMIN_IDS))
async def contact_cmd(client, message: Message):
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2: return await message.reply("/contact text | url\nExample: /contact 📞 Support | https://t.me/support")
        parts = args[1].split('|')
        if len(parts) >= 2:
            await db.update_contact({'text': parts[0].strip(), 'url': parts[1].strip()})
        else:
            await db.update_contact({'url': args[1].strip()})
        await message.reply("✅ Contact updated!")
    except Exception as e: await message.reply(f"❌ {e}")

@Client.on_message(filters.command('verify') & filters.user(ADMIN_IDS))
async def verify_cmd(client, message: Message):
    try:
        args = message.text.split()
        if len(args) < 2: return await message.reply("/verify pid")
        p = await db.get_payment(args[1])
        if p:
            await db.verify_payment(args[1], message.from_user.id)
            plan = await db.get_plan(p['plan_id'])
            if plan: await db.set_premium(p['user_id'], plan['duration_days'], plan['name'], plan.get('monitor_limit', 0), plan.get('check_interval', 0))
        await message.reply("✅ Verified!")
    except: pass

@Client.on_message(filters.command('reject') & filters.user(ADMIN_IDS))
async def reject_cmd(client, message: Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3: return await message.reply("/reject pid reason")
        pid, reason = args[1], args[2]
        p = await db.get_payment(pid)
        if p:
            await db.reject_payment(pid, message.from_user.id, reason)
            try: await client.send_message(p['user_id'], f"❌ Rejected: {reason}")
            except: pass
        await message.reply("✅ Rejected!")
    except: pass

@Client.on_message(filters.command('stats') & filters.user(ADMIN_IDS))
async def stats_cmd(client, message: Message):
    us = await db.get_stats()
    monitors = await db.get_all_active_monitors()
    up = sum(1 for m in monitors if m['status'] == 'up')
    pending = await db.get_pending_payments()
    await message.reply(f"📊 Users: {us['total_users']} | 💎{us['premium_users']}\n📊 Monitors: {len(monitors)} | 🟢{up}\n💳 Pending: {len(pending)}")

@Client.on_message(filters.command('export') & filters.user(ADMIN_IDS))
async def export_cmd(client, message: Message):
    text = await db.generate_file()
    with open("export.txt", 'w') as f: f.write(text)
    await message.reply_document("export.txt")

@Client.on_message(filters.command('broadcast') & filters.user(ADMIN_IDS))
async def broadcast_cmd(client, message: Message):
    if not message.reply_to_message: return await message.reply("Reply to a message!")
    users = await db.get_all_users()
    s = 0
    for u in users:
        try: await message.reply_to_message.copy(u['user_id']); s += 1
        except: pass
    await message.reply(f"📨 Sent: {s}/{len(users)}")

@Client.on_message(filters.command('tierview') & filters.user(ADMIN_IDS))
async def tier_view(client, message: Message):
    from config import FREE_TIER_LIMIT, PREMIUM_TIER_LIMIT, FREE_MONITOR_DURATION, PREMIUM_MONITOR_DURATION
    await message.reply(f"🆓 Free: {FREE_TIER_LIMIT} monitors, {FREE_MONITOR_DURATION}min\n💎 Premium: {PREMIUM_TIER_LIMIT} monitors, {PREMIUM_MONITOR_DURATION}min")

@Client.on_message(filters.command('tierset') & filters.user(ADMIN_IDS))
async def tier_set(client, message: Message):
    try:
        args = message.text.split()
        if len(args) < 5: return await message.reply("/tierset free_mon prem_mon free_int prem_int")
        import config
        config.FREE_TIER_LIMIT = int(args[1])
        config.PREMIUM_TIER_LIMIT = int(args[2])
        config.FREE_MONITOR_DURATION = int(args[3])
        config.PREMIUM_MONITOR_DURATION = int(args[4])
        await message.reply(f"✅ Updated!")
    except: pass

@Client.on_message(filters.command(['upi', 'bank', 'paypal']) & filters.user(ADMIN_IDS))
async def payment_settings_cmd(client, message: Message):
    cmd = message.command[0]
    if cmd == 'upi':
        args = message.text.split(maxsplit=1)
        if len(args) < 2: return await message.reply("/upi id@bank")
        await db.update_payment_method('upi', {'id': args[1], 'enabled': True})
        await message.reply(f"✅ UPI: {args[1]}")
    elif cmd == 'bank':
        args = message.text.split(maxsplit=1)
        if len(args) < 2: return await message.reply("/bank acc|ifsc|name")
        parts = args[1].split('|')
        if len(parts) < 3: return await message.reply("Need 3 values!")
        await db.update_payment_method('bank', {'details': {'account': parts[0], 'ifsc': parts[1], 'name': parts[2]}, 'enabled': True})
        await message.reply("✅ Bank updated!")

@Client.on_message(filters.command(['plans', 'addplan', 'delplan', 'toggleplan']) & filters.user(ADMIN_IDS))
async def plan_cmds(client, message: Message):
    cmd = message.command[0]
    if cmd == 'plans':
        plans = await db.get_plans()
        text = "📋 Plans\n\n"
        for p in plans: text += f"{p['plan_id']}: {p['name']} ₹{p['price']}\n"
        await message.reply(text)
    elif cmd == 'addplan':
        args = message.text.split(maxsplit=1)
        if len(args) < 2: return await message.reply("/addplan name|price|days|currency|limit|interval")
        parts = args[1].split('|')
        if len(parts) < 6: return await message.reply("Need 6 values!")
        plan = {'name': parts[0], 'price': float(parts[1]), 'duration_days': int(parts[2]), 'currency': parts[3], 'monitor_limit': int(parts[4]), 'check_interval': int(parts[5])}
        new = await db.add_plan(plan)
        await message.reply(f"✅ {new['name']}")
    elif cmd == 'delplan':
        args = message.text.split()
        if len(args) < 2: return await message.reply("/delplan id")
        await db.delete_plan(args[1])
        await message.reply("✅ Deleted!")
    elif cmd == 'toggleplan':
        args = message.text.split()
        if len(args) < 2: return await message.reply("/toggleplan id")
        p = await db.get_plan(args[1])
        if p: await db.update_plan(args[1], {'active': not p.get('active', True)})
        await message.reply("✅ Toggled!")
