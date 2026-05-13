from telegram import Update
from telegram.ext import ContextTypes
from models import User, Monitor, Payment, ForceJoin
from config import ADMIN_IDS
from datetime import datetime

class AdminE:
    def __init__(self, db):
        self.User = User(db)
        self.Monitor = Monitor(db)
        self.Payment = Payment(db)
        self.FJ = ForceJoin(db)
    
    # ============ PAYMENT ACTIONS ============
    
    async def cmd_pending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        pending = await self.Payment.get_pending()
        if not pending: await update.message.reply_text("✅ No pending!"); return
        text = "💳 Pending\n\n"
        for p in pending:
            text += f"🆔 {p['payment_id']}\n👤{p['user_id']} 💰{p['amount']}{p['currency']}\n/verify {p['payment_id']} | /reject {p['payment_id']}\n\n"
        await update.message.reply_text(text)
    
    async def cmd_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /verify pay_id"); return
            pid = context.args[0]
            p = await self.Payment.get(pid)
            if p:
                await self.Payment.verify(pid, update.effective_user.id)
                from models import PaymentSettings
                ps = PaymentSettings(self.User.collection.database)
                plan = await ps.get_plan(p['plan_id'])
                if plan: await self.User.set_premium(p['user_id'], plan['duration_days'], plan['name'])
                try: await context.bot.send_message(p['user_id'], "✅ Payment verified!")
                except: pass
            await update.message.reply_text(f"✅ {pid} verified!")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            args = context.args
            if len(args) < 2: await update.message.reply_text("❌ /reject pay_id reason"); return
            pid, reason = args[0], ' '.join(args[1:])
            p = await self.Payment.get(pid)
            if p:
                await self.Payment.reject(pid, update.effective_user.id, reason)
                try: await context.bot.send_message(p['user_id'], f"❌ Rejected: {reason}")
                except: pass
            await update.message.reply_text(f"✅ {pid} rejected!")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    # ============ FORCE JOIN ============
    
    async def cmd_fj_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        s = await self.FJ.get_settings()
        channels = s.get('channels', [])
        text = f"📢 Force Join ({'ON' if s.get('enabled') else 'OFF'})\n\n"
        for ch in channels:
            text += f"• {ch.get('name', 'N/A')} ({ch['id']})\n"
        if not channels: text += "No channels added!"
        await update.message.reply_text(text)
    
    async def cmd_fj_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 2: await update.message.reply_text("❌ /fjadd channel_id @username\nExample: /fjadd -100123 @channel"); return
            ch = {'id': int(context.args[0]), 'username': context.args[1].replace('@', ''), 'name': context.args[1], 'type': 'channel'}
            ok = await self.FJ.add_channel(ch)
            await update.message.reply_text(f"✅ Added!" if ok else "❌ Already exists!")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_fj_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /fjremove channel_id"); return
            await self.FJ.remove_channel(int(context.args[0]))
            await update.message.reply_text(f"✅ Removed!")
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_fj_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        s = await self.FJ.get_settings()
        await self.FJ.toggle(not s.get('enabled', False))
        await update.message.reply_text(f"✅ Force Join {'ON' if not s.get('enabled') else 'OFF'}!")
    
    # ============ STATS & EXPORT ============
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        us = await self.User.get_stats()
        monitors = await self.Monitor.get_all_monitors()
        up = sum(1 for m in monitors if m['status'] == 'up')
        pending = await self.Payment.get_pending()
        text = f"📊 Stats\n\n👥 Users: {us['total_users']}\n💎 Premium: {us['premium_users']}\n🆓 Free: {us['free_users']}\n🚫 Banned: {us['banned_users']}\n\n📊 Monitors: {len(monitors)}\n🟢 Up: {up} | 🔴 Down: {len(monitors)-up}\n\n💳 Pending: {len(pending)}"
        await update.message.reply_text(text)
    
    async def cmd_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        text = await self.Monitor.generate_file()
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f: f.write(text)
        await update.message.reply_document(open(filename, 'rb'), filename=filename)
    
    async def cmd_export_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        try:
            if len(context.args) < 1: await update.message.reply_text("❌ /exportuser userid"); return
            uid = int(context.args[0])
            text = await self.Monitor.generate_file(uid)
            filename = f"user_{uid}.txt"
            with open(filename, 'w') as f: f.write(text)
            await update.message.reply_document(open(filename, 'rb'), filename=filename)
        except Exception as e: await update.message.reply_text(f"❌ Error: {e}")
    
    # ============ BROADCAST ============
    
    async def cmd_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS: return
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Reply to a message to broadcast!")
            return
        users = await self.User.get_all_users()
        s, f = 0, 0
        for u in users:
            try:
                await update.message.reply_to_message.copy(u['user_id'])
                s += 1
            except: f += 1
        await update.message.reply_text(f"📨 Sent: {s}/{len(users)} | Failed: {f}")
