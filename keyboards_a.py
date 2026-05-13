from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def main_menu(user_id, admin_ids, contact):
    kb = [
        [InlineKeyboardButton("📊 My Monitors", callback_data="my_monitors"),
         InlineKeyboardButton("➕ Add Monitor", callback_data="add_monitor")],
        [InlineKeyboardButton("💎 Premium", callback_data="premium_menu"),
         InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton(f"📞 {contact.get('text', 'Contact')}", url=contact.get('url', 'https://t.me/admin'))]
    ]
    if user_id in admin_ids:
        kb.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

def back_button(cb): return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=cb)]])
def confirm_delete(mid): return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Delete", callback_data=f"confirmdel_{mid}"), InlineKeyboardButton("❌ No", callback_data=f"detail_{mid}")]])
def monitor_actions(mid): return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{mid}"), InlineKeyboardButton("⏸️ Toggle", callback_data=f"toggle_{mid}")], [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{mid}")], [InlineKeyboardButton("🔙 Back", callback_data="my_monitors")]])
def premium_plans(plans):
    kb = []
    for p in plans: kb.append([InlineKeyboardButton(f"💎 {p['name']} - ₹{p['price']}", callback_data=f"buy_{p['plan_id']}")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(kb)

def payment_methods(settings):
    kb = []
    m = settings.get('payment_methods', {})
    if m.get('upi', {}).get('enabled'): kb.append([InlineKeyboardButton("🇮🇳 UPI", callback_data="pay_upi")])
    if m.get('bank', {}).get('enabled'): kb.append([InlineKeyboardButton("🏦 Bank", callback_data="pay_bank")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="premium_menu")])
    return InlineKeyboardMarkup(kb)
