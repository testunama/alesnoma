from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from models import ForceJoin, User
from keyboards import fj_menu, back_button
from config import ADMIN_IDS

WAIT_FJ_CHANNEL, WAIT_BROADCAST = 8, 9

class AdminC:
    def __init__(self, db):
        self.FJ = ForceJoin(db)
        self.User = User(db)
    
    async def fj_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        s = await self.FJ.get_settings()
        await q.edit_message_text("📢 Force Join Settings", reply_markup=fj_menu(s['channels'], s['enabled']))
    
    async def fj_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        s = await self.FJ.get_settings()
        await self.FJ.toggle(not s['enabled'])
        await self.fj_menu(update, context)
    
    async def fj_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        await q.edit_message_text("📢 Add Channel/Group\n\nForward message from channel\nOR send @username\nOR send -100xxx ID\n\n/cancel")
        return WAIT_FJ_CHANNEL
    
    async def fj_receive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_info = None
        
        if update.message.forward_from_chat:
            chat = update.message.forward_from_chat
            chat_info = {
                'id': chat.id, 'username': chat.username or f"id{chat.id}",
                'name': chat.title or 'Unknown', 'type': chat.type,
                'invite_link': getattr(chat, 'invite_link', '')
            }
        elif update.message.text:
            text = update.message.text.strip()
            try:
                chat_id = int(text)
                try:
                    chat = await context.bot.get_chat(chat_id)
                    chat_info = {
                        'id': chat.id, 'username': chat.username or f"id{chat.id}",
                        'name': chat.title or 'Unknown', 'type': chat.type,
                        'invite_link': chat.invite_link or ''
                    }
                except:
                    await update.message.reply_text("❌ Cannot access! Bot must be admin.", reply_markup=back_button("fj_menu"))
                    return ConversationHandler.END
            except:
                if text.startswith('@'): text = text[1:]
                try:
                    chat = await context.bot.get_chat(f"@{text}")
                    chat_info = {
                        'id': chat.id, 'username': chat.username or text,
                        'name': chat.title or text, 'type': chat.type,
                        'invite_link': chat.invite_link or f"https://t.me/{text}"
                    }
                except:
                    await update.message.reply_text("❌ Chat not found!", reply_markup=back_button("fj_menu"))
                    return ConversationHandler.END
        
        if not chat_info:
            await update.message.reply_text("❌ Invalid!", reply_markup=back_button("fj_menu"))
            return ConversationHandler.END
        
        chat_info['added_by'] = update.message.from_user.id
        success = await self.FJ.add_channel(chat_info)
        
        if success:
            await update.message.reply_text(f"✅ Added: {chat_info['name']}\n@{chat_info['username']}", reply_markup=back_button("fj_menu"))
        else:
            await update.message.reply_text("❌ Already added!", reply_markup=back_button("fj_menu"))
        
        return ConversationHandler.END
    
    async def fj_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        channel_id = int(q.data.replace("fj_remove_", ""))
        await self.FJ.remove_channel(channel_id)
        await self.fj_menu(update, context)
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        await q.edit_message_text("📨 Send message to broadcast:")
        return WAIT_BROADCAST
    
    async def send_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        users = await self.User.get_all_users()
        success = 0
        for u in users:
            try:
                await update.message.copy(u['user_id'])
                success += 1
            except: pass
        
        await update.message.reply_text(f"📨 Sent: {success}/{len(users)}", reply_markup=back_button("admin"))
        return ConversationHandler.END
    
    async def check_joined_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        
        user_id = q.from_user.id
        if user_id in ADMIN_IDS:
            await q.edit_message_text("✅ Admin verified!", reply_markup=back_button("menu"))
            return
        
        joined, not_joined = await self.FJ.check_joined(user_id, context)
        
        if joined:
            await q.edit_message_text("✅ Verified! You can use bot now.", reply_markup=back_button("menu"))
        else:
            from keyboards import fj_menu
            kb = []
            for ch in not_joined:
                link = ch.get('invite_link', f"https://t.me/{ch.get('username', '')}")
                kb.append([InlineKeyboardButton(f"Join {ch.get('name', 'Channel')}", url=link)])
            kb.append([InlineKeyboardButton("🔄 Check Again", callback_data="check_joined")])
            
            await q.edit_message_text("⚠️ Join all channels first!", reply_markup=InlineKeyboardMarkup(kb))
    
    async def fj_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Cancelled.", reply_markup=back_button("fj_menu"))
        return ConversationHandler.END
