from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_disk_usage

async def disk_command(update: Update, context: CallbackContext) -> None:
    disk_usage = get_disk_usage()
    await update.message.reply_text(disk_usage)
