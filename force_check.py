from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import Database
from config import ADMIN_IDS

db = Database()

async def check_force_join(client, update):
    user_id = update.from_user.id if hasattr(update, 'from_user') else None
    if not user_id or user_id in ADMIN_IDS: return True
    
    settings = await db.get_fj_settings()
    if not settings or not settings.get('enabled'): return True
    
    channels = settings.get('channels', [])
    if not channels: return True
    
    not_joined = []
    for ch in channels:
        try:
            member = await client.get_chat_member(ch['id'], user_id)
            if member.status in ['left', 'kicked', 'banned']: not_joined.append(ch)
        except: not_joined.append(ch)
    
    if not_joined:
        text = "⚠️ **Join these channels to use bot!**\n\n"
        kb = []
        for ch in not_joined:
            link = ch.get('invite_link') or f"https://t.me/{ch.get('username', '')}"
            text += f"• {ch.get('name', 'Channel')}\n"
            kb.append([InlineKeyboardButton(f"📢 Join {ch.get('name', 'Channel')}", url=link)])
        kb.append([InlineKeyboardButton("🔄 Check Again", callback_data="check_fj")])
        
        if hasattr(update, 'edit_message_text'):
            await update.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        return False
    return True
