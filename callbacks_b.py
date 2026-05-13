from pyrogram import Client
from pyrogram.types import CallbackQuery, Message
from database import Database
from keyboards_a import *
from config import ADMIN_IDS

db = Database()
user_states = {}

async def premium_menu_cb(client, cb: CallbackQuery):
    plans = await db.get_plans()
    if not plans: return await cb.edit_message_text("No plans", reply_markup=back_button("main_menu"))
    await cb.edit_message_text("💎 Plans", reply_markup=premium_plans(plans))

async def select_method_cb(client, cb: CallbackQuery):
    pid = cb.data.replace("buy_", "")
    plan = await db.get_plan(pid)
    if not plan: return
    user_states[cb.from_user.id] = {'plan': plan}
    settings = await db.get_settings()
    await cb.edit_message_text(f"💎 {plan['name']} | ₹{plan['price']}", reply_markup=payment_methods(settings))

async def pay_upi_cb(client, cb: CallbackQuery):
    plan = user_states.get(cb.from_user.id, {}).get('plan')
    if not plan: return
    settings = await db.get_settings()
    upi = settings['payment_methods']['upi']['id']
    if not upi: return await cb.edit_message_text("UPI not set!", reply_markup=back_button("premium_menu"))
    
    payment = await db.create_payment(cb.from_user.id, plan['plan_id'], plan['price'], plan['currency'], 'upi')
    user_states[cb.from_user.id]['payment_id'] = payment['payment_id']
    user_states[cb.from_user.id]['waiting'] = 'screenshot'
    
    from utils import generate_qr
    qr = generate_qr(upi, plan['price'])
    text = f"💳 UPI\n💰 ₹{plan['price']}\n🏦 `{upi}`\n🆔 {payment['payment_id']}\n\n📸 Send screenshot:"
    
    if qr:
        await cb.message.delete()
        await client.send_photo(cb.from_user.id, qr, caption=text)
    else:
        await cb.edit_message_text(text)

async def pay_bank_cb(client, cb: CallbackQuery):
    plan = user_states.get(cb.from_user.id, {}).get('plan')
    if not plan: return
    settings = await db.get_settings()
    bank = settings['payment_methods']['bank']['details']
    payment = await db.create_payment(cb.from_user.id, plan['plan_id'], plan['price'], plan['currency'], 'bank')
    user_states[cb.from_user.id]['payment_id'] = payment['payment_id']
    user_states[cb.from_user.id]['waiting'] = 'screenshot'
    text = f"🏦 Bank\n💰 ₹{plan['price']}\n🏧 {bank.get('account','?')}\n🏦 {bank.get('ifsc','?')}\n👤 {bank.get('name','?')}\n🆔 {payment['payment_id']}\n\n📸 Send screenshot:"
    await cb.edit_message_text(text)

async def handle_screenshot(client, message: Message):
    uid = message.from_user.id
    if uid not in user_states or user_states[uid].get('waiting') != 'screenshot': return
    if not message.photo: return await message.reply_text("❌ Send image!")
    
    pid = user_states[uid].get('payment_id')
    await db.save_screenshot(pid, message.photo.file_id)
    
    payment = await db.get_payment(pid)
    for aid in ADMIN_IDS:
        try: await client.send_photo(aid, message.photo.file_id, caption=f"🆕 Payment\n🆔 {pid}\n👤 {uid}\n💰 {payment['amount']} {payment['currency']}")
        except: pass
    
    await message.reply_text("✅ Submitted!", reply_markup=back_button("main_menu"))
    user_states.pop(uid, None)
