# handlers/uptime_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_uptime

async def uptime_command(update: Update, context: CallbackContext) -> None:
    uptime = get_uptime()
    await update.message.reply_text(uptime)
