from pyrogram import Client, filters
from pyrogram.types import Message
from callbacks_b import handle_screenshot
from force_check import check_force_join

@Client.on_message(filters.photo & filters.private)
async def on_screenshot(client, message: Message):
    if not await check_force_join(client, message): return
    await handle_screenshot(client, message)
