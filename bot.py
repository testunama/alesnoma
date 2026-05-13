#!/usr/bin/env python3
import asyncio
import logging
import sys
import os
from flask import Flask
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from motor.motor_asyncio import AsyncIOMotorClient
from config import BOT_TOKEN, MONGODB_URI, ADMIN_IDS, PORT

from models import User, Monitor, PaymentSettings, Payment, ForceJoin
from keyboards import main_menu

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Running!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

# States - IMPORTANT: Unique numbers
(
    WAIT_URL, WAIT_NAME,
    WAIT_SS,
    WAIT_PLAN_NAME, WAIT_PLAN_PRICE, WAIT_PLAN_DURATION, WAIT_PLAN_CURRENCY,
    WAIT_PREMIUM_DAYS,
    WAIT_REJECT, WAIT_UPI, WAIT_PAYPAL,
    WAIT_FJ_CHANNEL, WAIT_BROADCAST
) = range(13)

class Bot:
    def __init__(self):
        self.db = None
        self.app = None
    
    async def init_db(self):
        try:
            logger.info("Connecting to MongoDB...")
            self.client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
            self.db = self.client.uptimebot
            await self.client.admin.command('ping')
            logger.info("✅ MongoDB Connected!")
            
            await PaymentSettings(self.db).init_default()
            await ForceJoin(self.db).init_default()
            return True
        except Exception as e:
            logger.error(f"❌ MongoDB Error: {e}")
            return False
    
    def build(self):
        from handlers_user import UserHandlers
        from handlers_payment import PaymentHandlers
        from admin_a import AdminA
        from admin_b import AdminB
        from admin_c import AdminC
        
        uh = UserHandlers(self.db)
        ph = PaymentHandlers(self.db)
        aa = AdminA(self.db)
        ab = AdminB(self.db)
        ac = AdminC(self.db)
        
        self.app = Application.builder().token(BOT_TOKEN).build()
        
        # ============ COMMANDS ============
        self.app.add_handler(CommandHandler('start', uh.start))
        self.app.add_handler(CommandHandler('help', uh.help_cmd))
        
        # ============ USER CALLBACKS ============
        self.app.add_handler(CallbackQueryHandler(uh.profile, pattern='^profile$'))
        self.app.add_handler(CallbackQueryHandler(uh.help_cmd, pattern='^help$'))
        self.app.add_handler(CallbackQueryHandler(uh.my_monitors, pattern='^my_monitors$'))
        self.app.add_handler(CallbackQueryHandler(uh.monitor_detail, pattern='^detail_'))
        self.app.add_handler(CallbackQueryHandler(uh.refresh_monitor, pattern='^refresh_'))
        self.app.add_handler(CallbackQueryHandler(uh.toggle_monitor, pattern='^toggle_'))
        self.app.add_handler(CallbackQueryHandler(uh.delete_monitor, pattern='^delete_'))
        self.app.add_handler(CallbackQueryHandler(uh.confirm_delete, pattern='^confirmdel_'))
        self.app.add_handler(CallbackQueryHandler(
            lambda u, c: u.callback_query.edit_message_text("🏠 Menu", reply_markup=main_menu(u.callback_query.from_user.id in ADMIN_IDS)),
            pattern='^menu$'
        ))
        
        # ============ PAYMENT CALLBACKS ============
        self.app.add_handler(CallbackQueryHandler(ph.premium_menu, pattern='^premium_menu$'))
        self.app.add_handler(CallbackQueryHandler(ph.select_method, pattern='^buy_'))
        
        # ============ ADMIN A CALLBACKS ============
        self.app.add_handler(CallbackQueryHandler(aa.panel, pattern='^admin$'))
        self.app.add_handler(CallbackQueryHandler(aa.users, pattern='^admin_users$'))
        self.app.add_handler(CallbackQueryHandler(aa.user_detail, pattern='^user_'))
        self.app.add_handler(CallbackQueryHandler(aa.ban_user, pattern='^ban_'))
        self.app.add_handler(CallbackQueryHandler(aa.export_user_monitors, pattern='^exportusr_'))
        self.app.add_handler(CallbackQueryHandler(aa.monitors, pattern='^admin_monitors$'))
        self.app.add_handler(CallbackQueryHandler(aa.export_all, pattern='^export_all$'))
        self.app.add_handler(CallbackQueryHandler(aa.stats, pattern='^admin_stats$'))
        self.app.add_handler(CallbackQueryHandler(aa.set_premium, pattern='^setprem_'))
        
        # ============ ADMIN B CALLBACKS ============
        self.app.add_handler(CallbackQueryHandler(ab.verify_payments, pattern='^verify_pay$'))
        self.app.add_handler(CallbackQueryHandler(ab.verify_payment, pattern='^verify_'))
        self.app.add_handler(CallbackQueryHandler(ab.reject_payment, pattern='^reject_'))
        self.app.add_handler(CallbackQueryHandler(ab.plans, pattern='^admin_plans$'))
        self.app.add_handler(CallbackQueryHandler(ab.plan_detail, pattern='^plan_'))
        self.app.add_handler(CallbackQueryHandler(ab.delete_plan, pattern='^delplan_'))
        self.app.add_handler(CallbackQueryHandler(ab.toggle_plan, pattern='^toggleplan_'))
        self.app.add_handler(CallbackQueryHandler(ab.payment_methods, pattern='^edit_methods$'))
        self.app.add_handler(CallbackQueryHandler(ab.edit_upi, pattern='^edit_upi$'))
        self.app.add_handler(CallbackQueryHandler(ab.edit_paypal, pattern='^edit_paypal$'))
        self.app.add_handler(CallbackQueryHandler(ab.add_plan, pattern='^addplan$'))
        
        # ============ ADMIN C CALLBACKS ============
        self.app.add_handler(CallbackQueryHandler(ac.fj_menu, pattern='^fj_menu$'))
        self.app.add_handler(CallbackQueryHandler(ac.fj_toggle, pattern='^fj_toggle$'))
        self.app.add_handler(CallbackQueryHandler(ac.fj_remove, pattern='^fj_remove_'))
        self.app.add_handler(CallbackQueryHandler(ac.check_joined_callback, pattern='^check_joined$'))
        self.app.add_handler(CallbackQueryHandler(ac.fj_add, pattern='^fj_add$'))
        self.app.add_handler(CallbackQueryHandler(ac.broadcast, pattern='^broadcast$'))
        
        # ============ CONVERSATIONS ============
        
        # Add Monitor
        add_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(uh.add_start, pattern='^add_monitor$')],
            states={
                WAIT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, uh.get_url)],
                WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, uh.get_name)]
            },
            fallbacks=[CommandHandler('cancel', uh.cancel)]
        )
        
        # Payment
        pay_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(ph.pay_upi, pattern='^pay_upi$'),
                CallbackQueryHandler(ph.pay_bank, pattern='^pay_bank$')
            ],
            states={
                WAIT_SS: [MessageHandler(filters.PHOTO, ph.receive_ss)]
            },
            fallbacks=[CommandHandler('cancel', ph.cancel)]
        )
        
        # Add Plan
        plan_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.add_plan, pattern='^addplan$')],
            states={
                WAIT_PLAN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_name)],
                WAIT_PLAN_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_price)],
                WAIT_PLAN_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_duration)],
                WAIT_PLAN_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_currency)]
            },
            fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
        )
        
        # Set Premium
        prem_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(aa.set_premium, pattern='^setprem_')],
            states={
                WAIT_PREMIUM_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, aa.set_premium_days)]
            },
            fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
        )
        
        # Reject Payment
        rej_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.reject_payment, pattern='^reject_')],
            states={
                WAIT_REJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.reject_reason)]
            },
            fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
        )
        
        # Edit UPI
        upi_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.edit_upi, pattern='^edit_upi$')],
            states={
                WAIT_UPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.save_upi)]
            },
            fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
        )
        
        # Edit PayPal
        pp_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.edit_paypal, pattern='^edit_paypal$')],
            states={
                WAIT_PAYPAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.save_paypal)]
            },
            fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
        )
        
        # Broadcast
        broad_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ac.broadcast, pattern='^broadcast$')],
            states={
                WAIT_BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND, ac.send_broadcast)]
            },
            fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
        )
        
        # Force Join Add
        fj_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ac.fj_add, pattern='^fj_add$')],
            states={
                WAIT_FJ_CHANNEL: [MessageHandler(filters.ALL & ~filters.COMMAND, ac.fj_receive)]
            },
            fallbacks=[CommandHandler('cancel', ac.fj_cancel)]
        )
        
        # Add all conversations
        self.app.add_handler(add_conv)
        self.app.add_handler(pay_conv)
        self.app.add_handler(plan_conv)
        self.app.add_handler(prem_conv)
        self.app.add_handler(rej_conv)
        self.app.add_handler(upi_conv)
        self.app.add_handler(pp_conv)
        self.app.add_handler(broad_conv)
        self.app.add_handler(fj_conv)
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
        
        logger.info("✅ Bot built successfully!")
    
    async def error_handler(self, update: Update, context):
        logger.error(f"Update {update} caused error: {context.error}")
        try:
            if update and update.callback_query:
                await update.callback_query.answer("⚠️ Error occurred. Try again!")
        except:
            pass
    
    async def start_bot(self):
        from utils import Scheduler
        
        scheduler = Scheduler(self.db, self.app.bot)
        scheduler.start()
        
        await self.app.bot.delete_webhook(drop_pending_updates=True)
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        logger.info("✅ Bot is running!")
        
        while True:
            await asyncio.sleep(3600)

async def main():
    bot = Bot()
    if await bot.init_db():
        bot.build()
        await bot.start_bot()
    else:
        logger.error("❌ Failed to initialize. Exiting...")
        sys.exit(1)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
