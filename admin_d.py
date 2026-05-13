from telegram import Update
from telegram.ext import ContextTypes
from models import User, PaymentSettings
from config import ADMIN_IDS, FREE_TIER_LIMIT, PREMIUM_TIER_LIMIT, FREE_MONITOR_DURATION, PREMIUM_MONITOR_DURATION
from datetime import datetime, timedelta

class AdminD:
    def __init__(self, db):
        self.User = User(db)
        self.PSettings = PaymentSettings(db)
    
    async def admin_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all admin commands"""
        if update.effective_user.id not in ADMIN_IDS:
            return
        
        text = """
🔐 *ADMIN COMMANDS*

👤 *User Management:*
/add userid days - Add premium
/remove userid - Remove premium
/ban userid - Ban user
/unban userid - Unban user
/users - List all users
/user userid - User details

💰 *Payment Settings:*
/upi your@upi - Set UPI ID
/paypal email - Set PayPal
/bank acc|ifsc|name - Set bank
Example: /bank 1234|SBIN|Name

📋 *Plan Management:*
/plans - View all plans
/addplan name|price|days|currency
/modifyplan id|name|price|days
/delplan plan_id
/toggleplan plan_id

⚙️ *Tier Settings:*
/tierview - View limits
/tierset free_mon premium_mon free_int premium_int
Example: /tierset 5 50 10 1

💳 *Payment Actions:*
/pending - Pending payments
/verify pay_id - Verify
/reject pay_id reason - Reject

📢 *Force Join:*
/fjchannels - List channels
/fjadd channel_id - Add channel
/fjremove channel_id - Remove
/fjtoggle - Toggle on/off

📊 *Other:*
/stats - Statistics
/export - Export monitors
/exportuser userid - Export user
/broadcast - Broadcast message
/adminhelp - This help
"""
        await update.message.reply_text(text, parse_mode='Markdown')
    
    # ============ USER COMMANDS ============
    
    async def cmd_add_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            return
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text("❌ /add userid days")
                return
            user_id, days = int(args[0]), int(args[1])
            await self.User.set_premium(user_id, days, "Admin")
            expiry = datetime.now() + timedelta(days=days)
            await update.message.reply_text(f"✅ Premium added!\nUser: {user_id}\nDays: {days}\nExpiry: {expiry.strftime('%d/%m/%Y')}")
            try: await context.bot.send_message(user_id, f"🎉 Admin gave you {days} days premium!")
            except: pass
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_remove_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            return
        try:
            if len(context.args) < 1:
                await update.message.reply_text("❌ /remove userid")
                return
            user_id = int(context.args[0])
            await self.User.collection.update_one({'user_id': user_id}, {'$set': {'is_premium': False, 'premium_expiry': datetime.now()}})
            await update.message.reply_text(f"✅ Premium removed from {user_id}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /ban userid"); return
            uid = int(context.args[0])
            await self.User.ban_user(uid, True)
            await update.message.reply_text(f"✅ {uid} banned!")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /unban userid"); return
            uid = int(context.args[0])
            await self.User.ban_user(uid, False)
            await update.message.reply_text(f"✅ {uid} unbanned!")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        users = await self.User.get_all_users()
        stats = await self.User.get_stats()
        text = f"👥 Users ({stats['total_users']})\n💎{stats['premium_users']} 🆓{stats['free_users']} 🚫{stats['banned_users']}\n\n"
        for u in users[:20]:
            b = "💎" if u.get('is_premium') else "🆓"
            x = "🚫" if u.get('is_banned') else ""
            text += f"{b}{x} {u['first_name'][:15]} [{u['user_id']}]\n"
        await update.message.reply_text(text)
    
    async def cmd_user_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /user userid"); return
            uid = int(context.args[0])
            u = await self.User.get_user(uid)
            if not u: await update.message.reply_text("Not found!"); return
            p = "❌" if not u.get('is_premium') else f"💎 {(u['premium_expiry']-datetime.now()).days}d"
            text = f"👤 {u['first_name']}\nID: {uid}\nPremium: {p}\nBanned: {u.get('is_banned')}\nMonitors: {u['monitor_count']}"
            await update.message.reply_text(text)
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    # ============ PAYMENT SETTINGS ============
    
    async def cmd_set_upi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /upi id@bank"); return
            await self.PSettings.update_method('upi', {'id': context.args[0], 'enabled': True})
            await update.message.reply_text(f"✅ UPI: {context.args[0]}")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_set_paypal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /paypal email"); return
            await self.PSettings.update_method('paypal', {'email': context.args[0], 'enabled': True})
            await update.message.reply_text(f"✅ PayPal: {context.args[0]}")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_set_bank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            text = ' '.join(context.args)
            parts = text.split('|')
            if len(parts) < 3: await update.message.reply_text("❌ /bank acc|ifsc|name"); return
            await self.PSettings.update_method('bank', {'details': {'account': parts[0], 'ifsc': parts[1], 'name': parts[2]}, 'enabled': True})
            await update.message.reply_text(f"✅ Bank: {parts[0]}")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    # ============ PLAN MANAGEMENT ============
    
    async def cmd_plans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        s = await self.PSettings.get_settings()
        plans = s.get('plans', [])
        text = "📋 Plans\n\n"
        for p in plans:
            st = "✅" if p.get('active', True) else "❌"
            text += f"{st} {p['plan_id']} - {p['name']}\n💰{p['price']}{p['currency']} 📅{p['duration_days']}d\n\n"
        await update.message.reply_text(text if plans else "No plans!")
    
    async def cmd_add_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            text = ' '.join(context.args)
            parts = text.split('|')
            if len(parts) < 4: await update.message.reply_text("❌ /addplan name|price|days|currency"); return
            plan = {'name': parts[0], 'price': float(parts[1]), 'duration_days': int(parts[2]), 'currency': parts[3].upper()}
            new = await self.PSettings.add_plan(plan)
            await update.message.reply_text(f"✅ Created: {new['name']} ({new['plan_id']})")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_modify_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            text = ' '.join(context.args)
            parts = text.split('|')
            if len(parts) < 4: await update.message.reply_text("❌ /modifyplan id|name|price|days"); return
            await self.PSettings.update_plan(parts[0], {'name': parts[1], 'price': float(parts[2]), 'duration_days': int(parts[3])})
            await update.message.reply_text(f"✅ Plan {parts[0]} updated!")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_delete_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /delplan id"); return
            await self.PSettings.delete_plan(context.args[0])
            await update.message.reply_text(f"✅ {context.args[0]} deleted!")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_toggle_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /toggleplan id"); return
            p = await self.PSettings.get_plan(context.args[0])
            if p: await self.PSettings.update_plan(context.args[0], {'active': not p.get('active', True)})
            await update.message.reply_text(f"✅ Toggled!")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    # ============ TIER SETTINGS ============
    
    async def cmd_tier_view(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        text = f"⚙️ Tiers\n\n🆓 Free: {FREE_TIER_LIMIT} monitors, {FREE_MONITOR_DURATION}min\n💎 Premium: {PREMIUM_TIER_LIMIT} monitors, {PREMIUM_MONITOR_DURATION}min\n\n/tierset free_mon premium_mon free_int premium_int"
        await update.message.reply_text(text)
    
    async def cmd_tier_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            args = context.args
            if len(args) < 4: await update.message.reply_text("❌ /tierset free_mon premium_mon free_int premium_int"); return
            import config
            config.FREE_TIER_LIMIT = int(args[0])
            config.PREMIUM_TIER_LIMIT = int(args[1])
            config.FREE_MONITOR_DURATION = int(args[2])
            config.PREMIUM_MONITOR_DURATION = int(args[3])
            await update.message.reply_text(f"✅ Updated!\nFree: {args[0]} monitors, {args[2]}min\nPremium: {args[1]} monitors, {args[3]}min")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
