# handlers/ping_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import ping_host

async def ping_command(update: Update, context: CallbackContext) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Please provide a host to ping.")
        return
    
    host = args[0]
    ping_result = ping_host(host)
    await update.message.reply_text(ping_result)
