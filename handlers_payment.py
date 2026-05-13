from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from models import PaymentSettings, Payment, User
from keyboards import premium_plans, payment_methods, back_button
from config import ADMIN_IDS

WAIT_SS = 1

class PaymentHandlers:
    def __init__(self, db):
        self.PSettings = PaymentSettings(db)
        self.Payment = Payment(db)
        self.User = User(db)
    
    async def premium_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        plans = await self.PSettings.get_plans()
        if not plans:
            await q.edit_message_text("No plans available.", reply_markup=back_button("menu"))
            return
        await q.edit_message_text("💎 Choose Plan", reply_markup=premium_plans(plans))
    
    async def select_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        plan_id = q.data.replace("buy_", "")
        plan = await self.PSettings.get_plan(plan_id)
        if not plan: return
        
        context.user_data['plan'] = plan
        settings = await self.PSettings.get_settings()
        await q.edit_message_text(f"💎 {plan['name']}\n💰 ₹{plan['price']}\n\nSelect payment:", reply_markup=payment_methods(settings))
    
    async def pay_upi(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        plan = context.user_data.get('plan')
        settings = await self.PSettings.get_settings()
        upi_id = settings['payment_methods']['upi']['id']
        
        if not upi_id:
            await q.edit_message_text("UPI not configured!", reply_markup=back_button("premium_menu"))
            return
        
        payment = await self.Payment.create(q.from_user.id, plan['plan_id'], plan['price'], plan['currency'], 'upi')
        context.user_data['pay_id'] = payment['payment_id']
        
        from utils import generate_qr
        qr = generate_qr(upi_id, plan['price'])
        
        text = f"💳 UPI Payment\n\n💰 ₹{plan['price']}\n🏦 UPI: {upi_id}\n🆔 {payment['payment_id']}\n\nSend payment screenshot:"
        
        if qr:
            await q.message.reply_photo(qr, caption=text)
        else:
            await q.edit_message_text(text)
        return WAIT_SS
    
    async def pay_bank(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        plan = context.user_data.get('plan')
        settings = await self.PSettings.get_settings()
        bank = settings['payment_methods']['bank']['details']
        
        payment = await self.Payment.create(q.from_user.id, plan['plan_id'], plan['price'], plan['currency'], 'bank')
        context.user_data['pay_id'] = payment['payment_id']
        
        text = f"🏦 Bank Transfer\n\n💰 ₹{plan['price']}\n🏧 A/C: {bank.get('account', 'N/A')}\n🏦 IFSC: {bank.get('ifsc', 'N/A')}\n👤 Name: {bank.get('name', 'N/A')}\n🆔 {payment['payment_id']}\n\nSend screenshot:"
        await q.edit_message_text(text)
        return WAIT_SS
    
    async def receive_ss(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.photo:
            await update.message.reply_text("❌ Send screenshot image!")
            return WAIT_SS
        
        pay_id = context.user_data.get('pay_id')
        if not pay_id:
            await update.message.reply_text("Session expired!", reply_markup=back_button("menu"))
            return ConversationHandler.END
        
        file_id = update.message.photo[-1].file_id
        await self.Payment.save_screenshot(pay_id, file_id)
        
        payment = await self.Payment.get(pay_id)
        user = update.message.from_user
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_photo(admin_id, file_id, caption=f"🆕 Payment\n🆔 {pay_id}\n👤 {user.id} (@{user.username})\n💰 {payment['amount']} {payment['currency']}\nMethod: {payment['method']}")
            except: pass
        
        await update.message.reply_text("✅ Submitted! Admin will verify soon.", reply_markup=back_button("menu"))
        context.user_data.clear()
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        await update.message.reply_text("Cancelled.", reply_markup=back_button("menu"))
        return ConversationHandler.END
