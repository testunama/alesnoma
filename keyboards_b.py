from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def admin_panel(): return InlineKeyboardMarkup([
    [InlineKeyboardButton("👥 Users", callback_data="admin_users"), InlineKeyboardButton("📊 Monitors", callback_data="admin_monitors")],
    [InlineKeyboardButton("💳 Payments", callback_data="verify_payments"), InlineKeyboardButton("📋 Plans", callback_data="admin_plans")],
    [InlineKeyboardButton("📢 Force Join", callback_data="fj_menu"), InlineKeyboardButton("🌐 Methods", callback_data="edit_methods")],
    [InlineKeyboardButton("📞 Contact", callback_data="edit_contact"), InlineKeyboardButton("📈 Stats", callback_data="admin_stats")],
    [InlineKeyboardButton("📨 Broadcast", callback_data="broadcast"), InlineKeyboardButton("📄 Export", callback_data="export_all")],
    [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
])

def users_list(users):
    kb = []
    for u in users[:20]: kb.append([InlineKeyboardButton(f"{'💎' if u.get('is_premium') else '🆓'} {u['first_name'][:20]}", callback_data=f"user_{u['user_id']}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

def user_actions(uid, banned): return InlineKeyboardMarkup([
    [InlineKeyboardButton("💎 Set Premium", callback_data=f"setprem_{uid}"), InlineKeyboardButton("🔓 Unban" if banned else "🔒 Ban", callback_data=f"ban_{uid}")],
    [InlineKeyboardButton("📄 Export", callback_data=f"exportusr_{uid}")], [InlineKeyboardButton("🔙 Back", callback_data="admin_users")]
])

def pending_kb(pending):
    kb = []
    for p in pending: kb.append([InlineKeyboardButton(f"✅ {p['payment_id'][:10]}", callback_data=f"verify_{p['payment_id']}"), InlineKeyboardButton("❌", callback_data=f"reject_{p['payment_id']}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

def fj_menu(channels, enabled): 
    kb = [[InlineKeyboardButton(f"Force Join: {'ON' if enabled else 'OFF'}", callback_data="fj_toggle")]]
    kb.append([InlineKeyboardButton("➕ Add", callback_data="fj_add")])
    for ch in channels: kb.append([InlineKeyboardButton(f"❌ {ch.get('name', '?')[:25]}", callback_data=f"fj_remove_{ch['id']}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)
