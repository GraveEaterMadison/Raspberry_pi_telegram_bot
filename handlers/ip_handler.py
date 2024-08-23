# handlers/ip_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_ip_addresses

async def ip_command(update: Update, context: CallbackContext) -> None:
    ip = get_ip_addresses()
    await update.message.reply_text(ip)
