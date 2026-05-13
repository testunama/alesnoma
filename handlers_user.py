from pyrogram import Client, filters
from pyrogram.types import Message
from database import Database
from keyboards_a import main_menu
from config import ADMIN_IDS
from force_check import check_force_join

db = Database()

@Client.on_message(filters.command('start'))
async def start_cmd(client, message: Message):
    if not await check_force_join(client, message): return
    
    user = message.from_user
    await db.create_user(user.id, user.username, user.first_name)
    u = await db.get_user(user.id)
    if u and u.get('is_banned'): return await message.reply("❌ Banned!")
    
    contact = await db.get_contact()
    await message.reply_text(f"Welcome {user.first_name}! 🚀\n\nFree: 3 monitors\nPremium: 20 monitors", reply_markup=await main_menu(user.id, ADMIN_IDS, contact))

@Client.on_message(filters.command('menu'))
async def menu_cmd(client, message: Message):
    if not await check_force_join(client, message): return
    contact = await db.get_contact()
    await message.reply_text("🏠 Menu", reply_markup=await main_menu(message.from_user.id, ADMIN_IDS, contact))
