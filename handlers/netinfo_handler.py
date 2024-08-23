# handlers/netinfo_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_netinfo

async def netinfo_command(update: Update, context: CallbackContext) -> None:
    netinfo = get_netinfo()
    await update.message.reply_text(netinfo)
