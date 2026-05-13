from pyrogram import Client, filters
from pyrogram.types import Message
from database import Database
from config import ADMIN_IDS

db = Database()

@Client.on_message(filters.command(['fjadd', 'fjremove', 'fjlist', 'fjtoggle']) & filters.user(ADMIN_IDS))
async def fj_cmds(client, message: Message):
    cmd = message.command[0]
    
    if cmd == 'fjlist':
        s = await db.get_fj_settings()
        text = f"📢 Force Join ({'ON' if s.get('enabled') else 'OFF'})\n\n"
        for ch in s.get('channels', []): text += f"• {ch.get('name', '?')} ({ch['id']})\n"
        await message.reply(text if s.get('channels') else "No channels!")
    
    elif cmd == 'fjtoggle':
        s = await db.get_fj_settings()
        await db.toggle_fj(not s.get('enabled'))
        await message.reply(f"✅ {'ON' if not s.get('enabled') else 'OFF'}!")
    
    elif cmd == 'fjadd':
        args = message.text.split()
        if len(args) < 2: return await message.reply("/fjadd -100id @username")
        try:
            ch_id = int(args[1])
            username = args[2].replace('@', '') if len(args) > 2 else ''
            name = args[2] if len(args) > 2 else str(ch_id)
            ok = await db.add_fj_channel({'id': ch_id, 'username': username, 'name': name, 'type': 'channel'})
            await message.reply("✅ Added!" if ok else "❌ Already exists!")
        except: await message.reply("❌ Invalid ID!")
    
    elif cmd == 'fjremove':
        args = message.text.split()
        if len(args) < 2: return await message.reply("/fjremove id")
        try:
            await db.remove_fj_channel(int(args[1]))
            await message.reply("✅ Removed!")
        except: pass
