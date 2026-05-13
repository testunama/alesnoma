#!/usr/bin/env python3
import asyncio, logging, sys, os
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from motor.motor_asyncio import AsyncIOMotorClient
from config import BOT_TOKEN, MONGODB_URI, ADMIN_IDS, PORT
from models import PaymentSettings, ForceJoin
from keyboards import main_menu

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Running!"
@app.route('/health')
def health(): return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=False)

(WAIT_URL, WAIT_NAME, WAIT_SS, WAIT_PLAN_NAME, WAIT_PLAN_PRICE, WAIT_PLAN_DURATION, WAIT_PLAN_CURRENCY, WAIT_PREMIUM_DAYS, WAIT_REJECT, WAIT_UPI, WAIT_PAYPAL, WAIT_FJ_CHANNEL, WAIT_BROADCAST) = range(13)

class Bot:
    def __init__(self):
        self.db = None
        self.app = None
    
    async def init_db(self):
        try:
            self.client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
            self.db = self.client.uptimebot
            await self.client.admin.command('ping')
            await PaymentSettings(self.db).init_default()
            await ForceJoin(self.db).init_default()
            logger.info("✅ MongoDB Connected!")
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
        from admin_d import AdminD
        from admin_e import AdminE
        
        uh = UserHandlers(self.db)
        ph = PaymentHandlers(self.db)
        aa = AdminA(self.db)
        ab = AdminB(self.db)
        ac = AdminC(self.db)
        ad = AdminD(self.db)
        ae = AdminE(self.db)
        
        self.app = Application.builder().token(BOT_TOKEN).build()
        
        # ============ COMMANDS (No conflicts) ============
        self.app.add_handler(CommandHandler('start', uh.start))
        self.app.add_handler(CommandHandler('help', uh.help_cmd))
        self.app.add_handler(CommandHandler('adminhelp', ad.admin_help))
        self.app.add_handler(CommandHandler('add', ad.cmd_add_premium))
        self.app.add_handler(CommandHandler('remove', ad.cmd_remove_premium))
        self.app.add_handler(CommandHandler('ban', ad.cmd_ban))
        self.app.add_handler(CommandHandler('unban', ad.cmd_unban))
        self.app.add_handler(CommandHandler('users', ad.cmd_users))
        self.app.add_handler(CommandHandler('user', ad.cmd_user_detail))
        self.app.add_handler(CommandHandler('upi', ad.cmd_set_upi))
        self.app.add_handler(CommandHandler('paypal', ad.cmd_set_paypal))
        self.app.add_handler(CommandHandler('bank', ad.cmd_set_bank))
        self.app.add_handler(CommandHandler('plans', ad.cmd_plans))
        self.app.add_handler(CommandHandler('addplan', ad.cmd_add_plan))
        self.app.add_handler(CommandHandler('modifyplan', ad.cmd_modify_plan))
        self.app.add_handler(CommandHandler('delplan', ad.cmd_delete_plan))
        self.app.add_handler(CommandHandler('toggleplan', ad.cmd_toggle_plan))
        self.app.add_handler(CommandHandler('tierview', ad.cmd_tier_view))
        self.app.add_handler(CommandHandler('tierset', ad.cmd_tier_set))
        self.app.add_handler(CommandHandler('pending', ae.cmd_pending))
        self.app.add_handler(CommandHandler('verify', ae.cmd_verify))
        self.app.add_handler(CommandHandler('reject', ae.cmd_reject))
        self.app.add_handler(CommandHandler('fjchannels', ae.cmd_fj_channels))
        self.app.add_handler(CommandHandler('fjadd', ae.cmd_fj_add))
        self.app.add_handler(CommandHandler('fjremove', ae.cmd_fj_remove))
        self.app.add_handler(CommandHandler('fjtoggle', ae.cmd_fj_toggle))
        self.app.add_handler(CommandHandler('stats', ae.cmd_stats))
        self.app.add_handler(CommandHandler('export', ae.cmd_export))
        self.app.add_handler(CommandHandler('exportuser', ae.cmd_export_user))
        self.app.add_handler(CommandHandler('broadcast', ae.cmd_broadcast))
        
        # ============ SIMPLE CALLBACKS (Not in any ConversationHandler) ============
        self.app.add_handler(CallbackQueryHandler(uh.profile, pattern='^profile$'))
        self.app.add_handler(CallbackQueryHandler(uh.help_cmd, pattern='^help$'))
        self.app.add_handler(CallbackQueryHandler(uh.my_monitors, pattern='^my_monitors$'))
        self.app.add_handler(CallbackQueryHandler(uh.monitor_detail, pattern='^detail_'))
        self.app.add_handler(CallbackQueryHandler(uh.refresh_monitor, pattern='^refresh_'))
        self.app.add_handler(CallbackQueryHandler(uh.toggle_monitor, pattern='^toggle_'))
        self.app.add_handler(CallbackQueryHandler(uh.delete_monitor, pattern='^delete_'))
        self.app.add_handler(CallbackQueryHandler(uh.confirm_delete, pattern='^confirmdel_'))
        self.app.add_handler(CallbackQueryHandler(ph.premium_menu, pattern='^premium_menu$'))
        self.app.add_handler(CallbackQueryHandler(ph.select_method, pattern='^buy_'))
        self.app.add_handler(CallbackQueryHandler(aa.panel, pattern='^admin$'))
        self.app.add_handler(CallbackQueryHandler(aa.users, pattern='^admin_users$'))
        self.app.add_handler(CallbackQueryHandler(aa.user_detail, pattern='^user_'))
        self.app.add_handler(CallbackQueryHandler(aa.ban_user, pattern='^ban_'))
        self.app.add_handler(CallbackQueryHandler(aa.export_user_monitors, pattern='^exportusr_'))
        self.app.add_handler(CallbackQueryHandler(aa.monitors, pattern='^admin_monitors$'))
        self.app.add_handler(CallbackQueryHandler(aa.export_all, pattern='^export_all$'))
        self.app.add_handler(CallbackQueryHandler(aa.stats, pattern='^admin_stats$'))
        self.app.add_handler(CallbackQueryHandler(ab.verify_payments, pattern='^verify_pay$'))
        self.app.add_handler(CallbackQueryHandler(ab.plans, pattern='^admin_plans$'))
        self.app.add_handler(CallbackQueryHandler(ab.plan_detail, pattern='^plan_'))
        self.app.add_handler(CallbackQueryHandler(ab.delete_plan, pattern='^delplan_'))
        self.app.add_handler(CallbackQueryHandler(ab.toggle_plan, pattern='^toggleplan_'))
        self.app.add_handler(CallbackQueryHandler(ab.payment_methods, pattern='^edit_methods$'))
        self.app.add_handler(CallbackQueryHandler(ac.fj_menu, pattern='^fj_menu$'))
        self.app.add_handler(CallbackQueryHandler(ac.fj_toggle, pattern='^fj_toggle$'))
        self.app.add_handler(CallbackQueryHandler(ac.fj_remove, pattern='^fj_remove_'))
        self.app.add_handler(CallbackQueryHandler(ac.check_joined_callback, pattern='^check_joined$'))
        self.app.add_handler(CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🏠 Menu", reply_markup=main_menu(u.callback_query.from_user.id in ADMIN_IDS)), pattern='^menu$'))
        
        # ============ CONVERSATIONS (Entry points NOT registered separately) ============
        
        add_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(uh.add_start, pattern='^add_monitor$')],
            states={WAIT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, uh.get_url)], WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, uh.get_name)]},
            fallbacks=[CommandHandler('cancel', uh.cancel)]
        )
        
        pay_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ph.pay_upi, pattern='^pay_upi$'), CallbackQueryHandler(ph.pay_bank, pattern='^pay_bank$')],
            states={WAIT_SS: [MessageHandler(filters.PHOTO, ph.receive_ss)]},
            fallbacks=[CommandHandler('cancel', ph.cancel)]
        )
        
        plan_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.add_plan, pattern='^addplan$')],
            states={WAIT_PLAN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_name)], WAIT_PLAN_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_price)], WAIT_PLAN_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_duration)], WAIT_PLAN_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.plan_currency)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        prem_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(aa.set_premium, pattern='^setprem_')],
            states={WAIT_PREMIUM_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, aa.set_premium_days)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        rej_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.reject_payment, pattern='^reject_')],
            states={WAIT_REJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.reject_reason)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        upi_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.edit_upi, pattern='^edit_upi$')],
            states={WAIT_UPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.save_upi)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        pp_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ab.edit_paypal, pattern='^edit_paypal$')],
            states={WAIT_PAYPAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ab.save_paypal)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        broad_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ac.broadcast, pattern='^broadcast$')],
            states={WAIT_BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND, ac.send_broadcast)]},
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        fj_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(ac.fj_add, pattern='^fj_add$')],
            states={WAIT_FJ_CHANNEL: [MessageHandler(filters.ALL & ~filters.COMMAND, ac.fj_receive)]},
            fallbacks=[CommandHandler('cancel', ac.fj_cancel)]
        )
        
        for conv in [add_conv, pay_conv, plan_conv, prem_conv, rej_conv, upi_conv, pp_conv, broad_conv, fj_conv]:
            self.app.add_handler(conv)
        
        self.app.add_error_handler(self.error)
        logger.info("✅ Bot built!")
    
    async def error(self, update, context):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.callback_query: await update.callback_query.answer("⚠️ Error!")
        except: pass
    
    async def start_bot(self):
        from utils import Scheduler
        Scheduler(self.db, self.app.bot).start()
        await self.app.bot.delete_webhook(drop_pending_updates=True)
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("✅ Bot running!")
        await asyncio.get_event_loop().create_future()

async def main():
    bot = Bot()
    if await bot.init_db():
        bot.build()
        await bot.start_bot()
    else:
        sys.exit(1)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
