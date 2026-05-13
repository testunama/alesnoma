from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from models import User, Monitor
from keyboards import main_menu, back_button, monitor_actions, confirm_delete
from config import ADMIN_IDS, ALLOWED_SCHEMES
from datetime import datetime

WAIT_URL, WAIT_NAME = range(2)

class UserHandlers:
    def __init__(self, db):
        self.User = User(db)
        self.Monitor = Monitor(db)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await self.User.create_user(user.id, user.username, user.first_name)
        db_user = await self.User.get_user(user.id)
        
        if db_user.get('is_banned'):
            await update.message.reply_text("❌ Your account is banned!")
            return
        
        text = f"Welcome {user.first_name}! 🚀\n\n✦ Free: 3 monitors | 5min\n✦ Premium: 20 monitors | 1min\n\nUse buttons below:"
        await update.message.reply_text(text, reply_markup=main_menu(user.id in ADMIN_IDS))
    
    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        u = await self.User.get_user(q.from_user.id)
        if not u: return
        
        premium = "❌ Free"
        if u.get('is_premium') and u.get('premium_expiry'):
            if u['premium_expiry'] > datetime.now():
                days = (u['premium_expiry'] - datetime.now()).days
                premium = f"💎 {u.get('premium_plan', 'Premium')} ({days}d)"
        
        limit = await self.User.get_monitor_limit(u['user_id'])
        dur = await self.User.get_monitor_duration(u['user_id'])
        
        text = f"""👤 Profile

ID: {u['user_id']}
Name: {u['first_name']}
Premium: {premium}
Monitors: {u['monitor_count']}/{limit}
Check Interval: {dur} min
Referral: {u['referral_code']}"""
        
        await q.edit_message_text(text, reply_markup=back_button("menu"))
    
    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = "ℹ️ Help\n\n✦ /start - Start\n✦ Add monitors via button\n✦ Premium for more features\n\nContact: @admin"
        if update.callback_query:
            q = update.callback_query
            await q.answer()
            await q.edit_message_text(text, reply_markup=back_button("menu"))
        else:
            await update.message.reply_text(text)
    
    async def my_monitors(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        monitors = await self.Monitor.get_user_monitors(q.from_user.id)
        
        if not monitors:
            await q.edit_message_text("No monitors yet! Click ➕ to add.", reply_markup=back_button("menu"))
            return
        
        text = "📊 Your Monitors\n\n"
        kb = []
        for m in monitors[:15]:
            emoji = "🟢" if m['status'] == 'up' else "🔴"
            text += f"{emoji} {m['name']} - {m['uptime_percentage']}%\n"
            kb.append([InlineKeyboardButton(f"{emoji} {m['name'][:30]}", callback_data=f"detail_{m['monitor_id']}")])
        
        kb.append([InlineKeyboardButton("➕ Add New", callback_data="add_monitor")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    
    async def monitor_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        mid = q.data.replace("detail_", "")
        m = await self.Monitor.get_monitor(mid)
        
        if not m or m['user_id'] != q.from_user.id:
            await q.answer("Not found!")
            return
        
        emoji = "🟢" if m['status'] == 'up' else "🔴"
        text = f"""{emoji} {m['name']}

🔗 {m['url']}
⏱ Interval: {m['check_interval']}min
📊 Uptime: {m['uptime_percentage']}%
✅ Success: {m['successful_checks']}
❌ Failed: {m['failed_checks']}
📅 Created: {m['created_at'].strftime('%d/%m/%Y')}"""
        
        await q.edit_message_text(text, reply_markup=monitor_actions(mid))
    
    async def refresh_monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer("Checking...")
        mid = q.data.replace("refresh_", "")
        m = await self.Monitor.get_monitor(mid)
        
        if m and m['user_id'] == q.from_user.id:
            from utils import check_website
            result = await check_website(m['url'])
            await self.Monitor.update_status(mid, result['status'], result.get('time', 0))
        
        await self.monitor_detail(update, context)
    
    async def toggle_monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        mid = q.data.replace("toggle_", "")
        m = await self.Monitor.get_monitor(mid)
        
        if m and m['user_id'] == q.from_user.id:
            new_status = not m['is_active']
            await self.Monitor.toggle_monitor(mid, new_status)
            await q.answer(f"{'Activated' if new_status else 'Paused'}!")
        
        await self.monitor_detail(update, context)
    
    async def delete_monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        mid = q.data.replace("delete_", "")
        m = await self.Monitor.get_monitor(mid)
        
        if m and m['user_id'] == q.from_user.id:
            await q.edit_message_text(f"⚠️ Delete {m['name']}?", reply_markup=confirm_delete(mid))
    
    async def confirm_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        mid = q.data.replace("confirmdel_", "")
        m = await self.Monitor.get_monitor(mid)
        
        if m and m['user_id'] == q.from_user.id:
            await self.Monitor.delete_monitor(mid)
            await self.User.dec_monitors(q.from_user.id)
        
        await self.my_monitors(update, context)
    
    async def add_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        
        limit = await self.User.get_monitor_limit(q.from_user.id)
        user = await self.User.get_user(q.from_user.id)
        
        if user['monitor_count'] >= limit:
            await q.edit_message_text(f"❌ Limit reached ({limit})! Upgrade to Premium.", reply_markup=back_button("premium_menu"))
            return ConversationHandler.END
        
        await q.edit_message_text("🔗 Send website URL:\nExample: https://example.com\n/cancel to abort")
        return WAIT_URL
    
    async def get_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        url = update.message.text.strip()
        if not any(url.startswith(s) for s in ALLOWED_SCHEMES):
            await update.message.reply_text("❌ Must start with http:// or https://")
            return WAIT_URL
        
        dup = await self.Monitor.check_duplicate(update.message.from_user.id, url)
        if dup:
            await update.message.reply_text("❌ Already monitoring this URL!")
            return WAIT_URL
        
        context.user_data['url'] = url
        await update.message.reply_text("✅ URL set!\nSend name for this monitor:")
        return WAIT_NAME
    
    async def get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = update.message.text.strip()
        url = context.user_data.get('url')
        user_id = update.message.from_user.id
        
        if not url:
            await update.message.reply_text("Error! Start again.")
            return ConversationHandler.END
        
        interval = await self.User.get_monitor_duration(user_id)
        m = await self.Monitor.create_monitor(user_id, url, name, interval)
        await self.User.inc_monitors(user_id)
        
        await update.message.reply_text(
            f"✅ Monitor Added!\n\n📛 {name}\n🔗 {url}\n⏱ {interval}min checks\n🆔 {m['monitor_id']}",
            reply_markup=back_button("my_monitors")
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        await update.message.reply_text("Cancelled.", reply_markup=back_button("menu"))
        return ConversationHandler.END
