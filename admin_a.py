from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from models import User, Monitor
from keyboards import admin_panel, back_button
from config import ADMIN_IDS

WAIT_PREMIUM_DAYS = 6

class AdminA:
    def __init__(self, db):
        self.User = User(db)
        self.Monitor = Monitor(db)
    
    async def panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        if q.from_user.id not in ADMIN_IDS: return
        await q.edit_message_text("⚙️ Admin Panel", reply_markup=admin_panel())
    
    async def users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        users = await self.User.get_all_users()
        stats = await self.User.get_stats()
        
        text = f"👥 Users ({stats['total_users']})\n💎 {stats['premium_users']} | 🆓 {stats['free_users']} | 🚫 {stats['banned_users']}\n\n"
        kb = []
        
        for u in users[:20]:
            badge = "💎" if u.get('is_premium') else "🆓"
            ban = "🚫" if u.get('is_banned') else ""
            text += f"{badge}{ban} {u['first_name'][:20]} [{u['user_id']}]\n"
            kb.append([InlineKeyboardButton(f"{badge} {u['first_name'][:25]} [{u['user_id']}]", callback_data=f"user_{u['user_id']}")])
        
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    
    async def user_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        uid = int(q.data.replace("user_", ""))
        u = await self.User.get_user(uid)
        if not u: return
        
        text = f"👤 {u['first_name']}\n\nID: {uid}\nUsername: @{u.get('username', 'N/A')}\nPremium: {u.get('is_premium')}\nBanned: {u.get('is_banned')}\nMonitors: {u['monitor_count']}\nJoined: {u['joined_at'].strftime('%d/%m/%Y')}"
        
        kb = [
            [InlineKeyboardButton("💎 Set Premium", callback_data=f"setprem_{uid}"),
             InlineKeyboardButton("🚫 Ban/Unban", callback_data=f"ban_{uid}")],
            [InlineKeyboardButton("📄 Export Monitors", callback_data=f"exportusr_{uid}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_users")]
        ]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    
    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        uid = int(q.data.replace("ban_", ""))
        u = await self.User.get_user(uid)
        await self.User.ban_user(uid, not u.get('is_banned'))
        await self.user_detail(update, context)
    
    async def set_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        uid = int(q.data.replace("setprem_", ""))
        context.user_data['prem_uid'] = uid
        await q.edit_message_text(f"Send days for user {uid}:")
        return WAIT_PREMIUM_DAYS
    
    async def set_premium_days(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            days = int(update.message.text)
            uid = context.user_data['prem_uid']
            await self.User.set_premium(uid, days, "Admin Grant")
            await update.message.reply_text(f"✅ Premium: {days} days", reply_markup=back_button("admin_users"))
            try: await context.bot.send_message(uid, f"🎉 Admin gave you {days} days premium!")
            except: pass
            return ConversationHandler.END
        except:
            await update.message.reply_text("Invalid! Send number:")
            return WAIT_PREMIUM_DAYS
    
    async def export_user_monitors(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        uid = int(q.data.replace("exportusr_", ""))
        text = await self.Monitor.generate_file(uid)
        file = f"user_{uid}_monitors.txt"
        with open(file, 'w') as f: f.write(text)
        await q.message.reply_document(open(file, 'rb'), filename=file)
    
    async def monitors(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        monitors = await self.Monitor.get_all_monitors()
        up = sum(1 for m in monitors if m['status'] == 'up')
        down = sum(1 for m in monitors if m['status'] == 'down')
        
        text = f"📊 All Monitors\n\n🟢 Up: {up}\n🔴 Down: {down}\n\n"
        for m in monitors[:10]:
            emoji = "🟢" if m['status'] == 'up' else "🔴"
            text += f"{emoji} {m['name'][:30]}\n  Uptime: {m['uptime_percentage']}% | User: {m['user_id']}\n"
        
        kb = [[InlineKeyboardButton("📄 Export All", callback_data="export_all")],
              [InlineKeyboardButton("🔙 Back", callback_data="admin")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    
    async def export_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        text = await self.Monitor.generate_file()
        file = "all_monitors.txt"
        with open(file, 'w') as f: f.write(text)
        await q.message.reply_document(open(file, 'rb'), filename=file)
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        us = await self.User.get_stats()
        monitors = await self.Monitor.get_all_monitors()
        up = sum(1 for m in monitors if m['status'] == 'up')
        
        text = f"""📊 Statistics

👥 Users: {us['total_users']}
💎 Premium: {us['premium_users']}
🆓 Free: {us['free_users']}
🚫 Banned: {us['banned_users']}

📊 Monitors: {len(monitors)}
🟢 Up: {up}
🔴 Down: {len(monitors)-up}"""
        await q.edit_message_text(text, reply_markup=back_button("admin"))
