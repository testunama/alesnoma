from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu(is_admin=False):
    kb = [
        [InlineKeyboardButton("📊 My Monitors", callback_data="my_monitors"),
         InlineKeyboardButton("➕ Add Monitor", callback_data="add_monitor")],
        [InlineKeyboardButton("💎 Premium", callback_data="premium_menu"),
         InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    if is_admin:
        kb.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

def admin_panel():
    kb = [
        [InlineKeyboardButton("👥 Users", callback_data="admin_users"),
         InlineKeyboardButton("📊 Monitors", callback_data="admin_monitors")],
        [InlineKeyboardButton("💳 Verify Payments", callback_data="verify_pay"),
         InlineKeyboardButton("📋 Plans", callback_data="admin_plans")],
        [InlineKeyboardButton("📢 Force Join", callback_data="fj_menu"),
         InlineKeyboardButton("🌐 Payment Methods", callback_data="edit_methods")],
        [InlineKeyboardButton("📨 Broadcast", callback_data="broadcast"),
         InlineKeyboardButton("📈 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📄 Export All", callback_data="export_all"),
         InlineKeyboardButton("🔙 Back", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(kb)

def back_button(callback):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=callback)]])

def monitor_actions(mid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{mid}"),
         InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{mid}")],
        [InlineKeyboardButton("⏸️ Toggle", callback_data=f"toggle_{mid}")],
        [InlineKeyboardButton("🔙 Back", callback_data="my_monitors")]
    ])

def confirm_delete(mid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes Delete", callback_data=f"confirmdel_{mid}"),
         InlineKeyboardButton("❌ No", callback_data=f"detail_{mid}")]
    ])

def premium_plans(plans):
    kb = []
    for p in plans:
        kb.append([InlineKeyboardButton(f"💎 {p['name']} - ₹{p['price']}", callback_data=f"buy_{p['plan_id']}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
    return InlineKeyboardMarkup(kb)

def payment_methods(settings):
    kb = []
    methods = settings.get('payment_methods', {})
    if methods.get('upi', {}).get('enabled'):
        kb.append([InlineKeyboardButton("🇮🇳 UPI Payment", callback_data="pay_upi")])
    if methods.get('paypal', {}).get('enabled'):
        kb.append([InlineKeyboardButton("🌍 PayPal", callback_data="pay_pp")])
    if methods.get('bank', {}).get('enabled'):
        kb.append([InlineKeyboardButton("🏦 Bank Transfer", callback_data="pay_bank")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="premium_menu")])
    return InlineKeyboardMarkup(kb)

def fj_menu(channels, enabled):
    kb = []
    status = "🟢 ON" if enabled else "🔴 OFF"
    kb.append([InlineKeyboardButton(f"Force Join: {status}", callback_data="fj_toggle")])
    kb.append([InlineKeyboardButton("➕ Add Channel/Group", callback_data="fj_add")])
    for ch in channels:
        emoji = "📢" if ch.get('type') == 'channel' else "👥"
        kb.append([
            InlineKeyboardButton(f"{emoji} {ch.get('name', 'Unknown')[:25]}", callback_data=f"fj_info_{ch['id']}"),
            InlineKeyboardButton("❌", callback_data=f"fj_remove_{ch['id']}")
        ])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

def payment_methods_admin(settings):
    kb = []
    methods = settings.get('payment_methods', {})
    for key, data in methods.items():
        status = "✅" if data.get('enabled') else "❌"
        kb.append([InlineKeyboardButton(f"{status} {data['name']}", callback_data=f"edit_{key}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin")])
    return InlineKeyboardMarkup(kb)
