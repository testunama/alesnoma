#!/usr/bin/env python3
import asyncio
import logging
import sys
from flask import Flask
from threading import Thread

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from motor.motor_asyncio import AsyncIOMotorClient
from config import BOT_TOKEN, MONGODB_URI, ADMIN_IDS, PORT

# Models
from models import User, Monitor, PaymentSettings, Payment, ForceJoin

# Handlers
from handlers_user import UserHandlers
from handlers_payment import PaymentHandlers
from admin_a import AdminA
from admin_b import AdminB
from admin_c import AdminC

# Utils
from utils import Scheduler
from keyboards import main_menu

# States
WAIT_URL, WAIT_NAME = range(2)
WAIT_SS = 2
WAIT_PLAN_NAME, WAIT_PLAN_PRICE, WAIT_PLAN_DURATION, WAIT_PLAN_CURRENCY = range(3, 7)
WAIT_PREMIUM_DAYS, WAIT_BROADCAST, WAIT_UPI, WAIT_REJECT, WAIT_PAYPAL = range(7, 12)
WAIT_FJ_CHANNEL = 12

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

class Bot:
    def __init__(self):
        self.db = None
        self.application = None
    
    async def init(self):
        try:
            logger.info("Connecting MongoDB...")
            self.client = AsyncIOMotorClient(MONGODB_URI)
            self.db = self.client.uptimebot
            
            await self.client.admin.command('ping')
            logger.info("✅ MongoDB Connected!")
            
            # Init defaults
            await PaymentSettings(self.db).init_default()
            await ForceJoin(self.db).init_default()
            
            logger.info("✅ Initialized!")
        except Exception as e:
            logger.error(f"❌ Init error: {e}")
            sys.exit(1)
    
    def build(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Handlers init
        uh = UserHandlers(self.db)
        ph = PaymentHandlers(self.db)
        aa = AdminA(self.db)
        ab = AdminB(self.db)
        ac = AdminC(self.db)
        
        # Commands
        self.application.add_handler(CommandHandler('start', uh.start))
        self.application.add_handler(CommandHandler('help', uh.help_cmd))
        
        # User callbacks
        self.application.add_handler(CallbackQueryHandler(uh.profile, pattern='^profile$'))
        self.application.add_handler(CallbackQueryHandler(uh.help_cmd, pattern='^help$'))
        self.application.add_handler(CallbackQueryHandler(uh.my_monitors, pattern='^my_monitors$'))
        self.application.add_handler(CallbackQueryHandler(uh.monitor_detail, pattern='^detail_'))
        self.application.add_handler(CallbackQueryHandler(uh.refresh_monitor, pattern='^refresh_'))
        self.application.add_handler(CallbackQueryHandler(uh.toggle_monitor, pattern='^toggle_'))
        self.application.add_handler(CallbackQueryHandler(uh.delete_monitor, pattern='^delete_'))
        self.application.add_handler(CallbackQueryHandler(uh.confirm_delete, pattern='^confirmdel_'))
        self.application.add_handler(CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🏠 Menu", reply_markup=main_menu(u.callback_query.from_user.id in ADMIN_IDS)), pattern='^menu$'))
        
        # Payment callbacks
        self.application.add_handler(CallbackQueryHandler(ph.premium_menu, pattern='^premium_menu$'))
        self.application.add_handler(CallbackQueryHandler(ph.select_method, pattern='^buy_'))
        self.application.add_handler(CallbackQueryHandler(ph.pay_upi, pattern='^pay_upi$'))
        self.application.add_handler(CallbackQueryHandler(ph.pay_bank, pattern='^pay_bank$'))
        
        # Admin A callbacks
        self.application.add_handler(CallbackQueryHandler(aa.panel, pattern='^admin$'))
        self.application.add_handler(CallbackQueryHandler(aa.users, pattern='^admin_users$'))
        self.application.add_handler(CallbackQueryHandler(aa.user_detail, pattern='^user_'))
        self.application.add_handler(CallbackQueryHandler(aa.ban_user, pattern='^ban_'))
        self.application.add_handler(CallbackQueryHandler(aa.export_user_monitors, pattern='^exportusr_'))
        self.application.add_handler(CallbackQueryHandler(aa.monitors, pattern='^admin_monitors$'))
        self.application.add_handler(CallbackQueryHandler(aa.export_all, pattern='^export_all$'))
        self.application.add_handler(CallbackQueryHandler(aa.stats, pattern='^admin_stats$'))
        
        # Admin B callbacks
        self.application.add_handler(CallbackQueryHandler(ab.verify_payments, pattern='^verify_pay$'))
        self.application.add_handler(CallbackQueryHandler(ab.verify_payment, pattern='^verify_'))
        self.application.add_handler(CallbackQueryHandler(ab.plans, pattern='^admin_plans$'))
        self.application.add_handler(CallbackQueryHandler(ab.plan_detail, pattern='^plan_'))
        self.application.add_handler(CallbackQueryHandler(ab.delete_plan, pattern='^delplan_'))
        self.application.add_handler(CallbackQueryHandler(ab.toggle_plan, pattern='^toggleplan_'))
        self.application.add_handler(CallbackQueryHandler(ab.payment_methods, pattern='^edit_methods$'))
        self.application.add_handler(CallbackQueryHandler(ab.edit_upi, pattern='^edit_upi$'))
        self.application.add_handler(CallbackQueryHandler(ab.edit_paypal, pattern='^edit_paypal$'))
        
        # Admin C callbacks
        self.application.add_handler(CallbackQueryHandler(ac.fj_menu, pattern='^fj_menu$'))
        self.application.add_handler(CallbackQueryHandler(ac.fj_toggle, pattern='^fj_toggle$'))
        self.application.add_handler(CallbackQueryHandler(ac.fj_remove, pattern='^fj_remove_'))
        self.application.add_handler(CallbackQueryHandler(ac.check_joined_callback, pattern='^check_joined$'))
        
        # Conversations
        add_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(uh.add_start, pattern='^add_monitor$')],
            states={
                WAIT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, uh.get_url)],
                WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, uh.get_name)]
            },
            fallbacks=[CommandHandler('cancel', uh.cancel)]
        )
        
        payment_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(ph.pay_upi, pattern='^pay_upi$'),
                CallbackQueryHandler(ph.pay_bank, pattern='^pay_bank$')
            ],
            states={WAIT_SS: [MessageHandler(filters.PHOTO, ph.receive_ss)]},
            fallbacks=[CommandHandler('cancel', ph.cancel)]
        )
        
        add_plan_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.add_plan, pattern='^addplan$')],
            states={
                WAIT_PLAN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_name)],
                WAIT_PLAN_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_price)],
                WAIT_PLAN_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_duration)],
                WAIT_PLAN_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_currency)]
            },
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        set_prem_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(aa.set_premium, pattern='^setprem_')],
            states={WAIT_PREMIUM_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, aa.set_premium_days)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        reject_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.reject_payment, pattern='^reject_')],
            states={WAIT_REJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.reject_reason)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        upi_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.edit_upi, pattern='^edit_upi$')],
            states={WAIT_UPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.save_upi)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        paypal_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.edit_paypal, pattern='^edit_paypal$')],
            states={WAIT_PAYPAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.save_paypal)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        broadcast_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ac.broadcast, pattern='^broadcast$')],
            states={WAIT_BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND, ac.send_broadcast)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        fj_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ac.fj_add, pattern='^fj_add$')],
            states={WAIT_FJ_CHANNEL: [MessageHandler(filters.ALL & ~filters.COMMAND, ac.fj_receive)]},
            fallbacks=[CommandHandler('cancel', ac.fj_cancel)]
        )
        
        # Add all conversations
        self.application.add_handler(add_conv)
        self.application.add_handler(payment_conv)
        self.application.add_handler(add_plan_conv)
        self.application.add_handler(set_prem_conv)
        self.application.add_handler(reject_conv)
        self.application.add_handler(upi_conv)
        self.application.add_handler(paypal_conv)
        self.application.add_handler(broadcast_conv)
        self.application.add_handler(fj_conv)
        
        self.application.add_error_handler(self.error)
        logger.info("✅ Bot built!")
    
    async def error(self, update: Update, context):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.callback_query:
                await update.callback_query.answer("Error occurred!")
        except: pass
    
    async def run(self):
        await self.init()
        self.build()
        
        # Start scheduler
        scheduler = Scheduler(self.db, self.application.bot)
        scheduler.start()
        
        # Start bot
        await self.application.bot.delete_webhook(drop_pending_updates=True)
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("✅ Bot running!")
        
        # Keep alive
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    # Start Flask
    Thread(target=run_flask).start()
    
    # Start bot
    bot = Bot()
    asyncio.run(bot.run())
