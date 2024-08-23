# handlers/temp_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_cpu_temperature

async def temperature_command(update: Update, context: CallbackContext) -> None:
    temp = get_cpu_temperature()
    await update.message.reply_text(temp)
