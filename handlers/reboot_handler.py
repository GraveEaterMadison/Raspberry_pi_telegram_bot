# handlers/reboot_handler.py
from telegram import Update
from telegram.ext import CallbackContext
import os

async def reboot_command(update: Update, context: CallbackContext) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Rebooting now...")
        os.system('sudo reboot')
        return

    try:
        if args[0] == 'at':
            time = args[1]
            await update.message.reply_text(f"Rebooting at {time}...")
            os.system(f'sudo shutdown -r {time}')
        elif args[0] == 'in':
            time = args[1]
            await update.message.reply_text(f"Rebooting in {time}...")
            os.system(f'sudo shutdown -r +{time}')
        else:
            await update.message.reply_text("Invalid command format.")
    except IndexError:
        await update.message.reply_text("Please provide a valid time argument.")
