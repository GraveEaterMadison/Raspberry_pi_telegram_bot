from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_cpu_usage

async def cpu_command(update: Update, context: CallbackContext) -> None:
    cpu_usage = get_cpu_usage()
    await update.message.reply_text(cpu_usage)
