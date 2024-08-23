# handlers/shutdown_handler.py
from telegram import Update
from telegram.ext import CallbackContext
import os

async def shutdown_command(update: Update, context: CallbackContext) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Shutting down now...")
        os.system('sudo shutdown now')
        return

    try:
        if args[0] == 'at':
            time = args[1]
            await update.message.reply_text(f"Shutting down at {time}...")
            os.system(f'sudo shutdown {time}')
        elif args[0] == 'in':
            time = args[1]
            await update.message.reply_text(f"Shutting down in {time}...")
            os.system(f'sudo shutdown +{time}')
        else:
            await update.message.reply_text("Invalid command format.")
    except IndexError:
        await update.message.reply_text("Please provide a valid time argument.")
