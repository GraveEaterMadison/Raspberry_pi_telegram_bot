# handlers/info_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_system_info

async def info_command(update: Update, context: CallbackContext) -> None:
    info = get_system_info()
    await update.message.reply_text(info)
