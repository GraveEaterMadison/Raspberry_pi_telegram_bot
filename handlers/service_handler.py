# handlers/service_handler.py
from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import manage_service

async def service_command(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /service <action> <service_name>\nActions: start, stop, status, restart")
        return

    action = args[0]
    service = args[1]

    try:
        result = manage_service(action, service)
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"Error managing service: {e}")
