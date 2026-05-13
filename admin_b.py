from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from models import PaymentSettings, Payment, User
from keyboards import back_button, payment_methods_admin
from config import ADMIN_IDS

WAIT_PLAN_NAME, WAIT_PLAN_PRICE, WAIT_PLAN_DURATION, WAIT_PLAN_CURRENCY = range(4)
WAIT_REJECT, WAIT_UPI, WAIT_PAYPAL = range(4, 7)

class AdminB:
    def __init__(self, db):
        self.PSettings = PaymentSettings(db)
        self.Payment = Payment(db)
        self.User = User(db)
    
    async def verify_payments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        pending = await self.Payment.get_pending()
        
        if not pending:
            await q.edit_message_text("✅ No pending!", reply_markup=back_button("admin"))
            return
        
        text = "💳 Pending Payments\n\n"
        kb = []
        for p in pending:
            text += f"🆔 {p['payment_id']}\n👤 {p['user_id']}\n💰 {p['amount']} {p['currency']}\n📅 {p['created_at'].strftime('%d/%m %H:%M')}\n\n"
            kb.append([
                InlineKeyboardButton(f"✅ {p['payment_id'][:8]}", callback_data=f"verify_{p['payment_id']}"),
                InlineKeyboardButton("❌", callback_data=f"reject_{p['payment_id']}")
            ])
        
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    
    async def verify_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        pid = q.data.replace("verify_", "")
        p = await self.Payment.get(pid)
        
        if p:
            await self.Payment.verify(pid, q.from_user.id)
            plan = await self.PSettings.get_plan(p['plan_id'])
            if plan:
                await self.User.set_premium(p['user_id'], plan['duration_days'], plan['name'])
            try: await context.bot.send_message(p['user_id'], "✅ Payment verified! Premium activated!")
            except: pass
        
        await q.answer("Verified!")
        await self.verify_payments(update, context)
    
    async def reject_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        pid = q.data.replace("reject_", "")
        context.user_data['reject_pid'] = pid
        await q.edit_message_text(f"Send rejection reason for {pid}:")
        return WAIT_REJECT
    
    async def reject_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pid = context.user_data['reject_pid']
        reason = update.message.text
        p = await self.Payment.get(pid)
        
        await self.Payment.reject(pid, update.message.from_user.id, reason)
        if p:
            try: await context.bot.send_message(p['user_id'], f"❌ Payment rejected\nReason: {reason}")
            except: pass
        
        await update.message.reply_text("✅ Rejected", reply_markup=back_button("admin"))
        return ConversationHandler.END
    
    async def plans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        plans = await self.PSettings.get_plans()
        text = "📋 Plans\n\n"
        kb = []
        
        for p in plans:
            text += f"{'✅' if p.get('active') else '❌'} {p['name']} - ₹{p['price']}\n"
            kb.append([InlineKeyboardButton(f"{p['name']}", callback_data=f"plan_{p['plan_id']}")])
        
        kb.append([InlineKeyboardButton("➕ New Plan", callback_data="addplan")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    
    async def plan_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        pid = q.data.replace("plan_", "")
        p = await self.PSettings.get_plan(pid)
        if not p: return
        
        text = f"📋 {p['name']}\n💰 {p['price']} {p['currency']}\n📅 {p['duration_days']} days\nActive: {p.get('active', True)}"
        kb = [
            [InlineKeyboardButton("🗑️ Delete", callback_data=f"delplan_{pid}"),
             InlineKeyboardButton("Toggle", callback_data=f"toggleplan_{pid}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_plans")]
        ]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    
    async def add_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        await q.edit_message_text("Send plan name:")
        return WAIT_PLAN_NAME
    
    async def plan_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['plan'] = {'name': update.message.text}
        await update.message.reply_text("Price (number):")
        return WAIT_PLAN_PRICE
    
    async def plan_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data['plan']['price'] = float(update.message.text)
            await update.message.reply_text("Duration (days):")
            return WAIT_PLAN_DURATION
        except:
            await update.message.reply_text("Invalid! Number:")
            return WAIT_PLAN_PRICE
    
    async def plan_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            context.user_data['plan']['duration_days'] = int(update.message.text)
            await update.message.reply_text("Currency (INR/USD):")
            return WAIT_PLAN_CURRENCY
        except:
            await update.message.reply_text("Invalid! Number:")
            return WAIT_PLAN_DURATION
    
    async def plan_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['plan']['currency'] = update.message.text.upper()
        new = await self.PSettings.add_plan(context.user_data['plan'])
        await update.message.reply_text(f"✅ Created: {new['name']}", reply_markup=back_button("admin_plans"))
        context.user_data.clear()
        return ConversationHandler.END
    
    async def delete_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        pid = q.data.replace("delplan_", "")
        await self.PSettings.delete_plan(pid)
        await self.plans(update, context)
    
    async def toggle_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        pid = q.data.replace("toggleplan_", "")
        p = await self.PSettings.get_plan(pid)
        if p:
            await self.PSettings.update_plan(pid, {'active': not p.get('active')})
        await self.plans(update, context)
    
    async def payment_methods(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        settings = await self.PSettings.get_settings()
        await q.edit_message_text("🌐 Payment Methods", reply_markup=payment_methods_admin(settings))
    
    async def edit_upi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        await q.edit_message_text("Send new UPI ID:")
        return WAIT_UPI
    
    async def save_upi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.PSettings.update_method('upi', {'id': update.message.text, 'enabled': True})
        await update.message.reply_text("✅ UPI updated!", reply_markup=back_button("admin"))
        return ConversationHandler.END
    
    async def edit_paypal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        await q.edit_message_text("Send PayPal email:")
        return WAIT_PAYPAL
    
    async def save_paypal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.PSettings.update_method('paypal', {'email': update.message.text, 'enabled': True})
        await update.message.reply_text("✅ PayPal updated!", reply_markup=back_button("admin"))
        return ConversationHandler.END
