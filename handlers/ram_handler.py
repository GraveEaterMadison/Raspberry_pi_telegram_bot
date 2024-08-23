# handlers/ram_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_ram_usage

async def ram_command(update: Update, context: CallbackContext) -> None:
    ram_usage = get_ram_usage()
    await update.message.reply_text(ram_usage)
