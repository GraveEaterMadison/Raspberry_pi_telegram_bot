from telegram import Update
from telegram.ext import CallbackContext
import subprocess

async def exec_command_handler(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Please provide a command to execute.")
        return

    command = " ".join(context.args)
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        await update.message.reply_text(result.decode('utf-8'))
    except subprocess.CalledProcessError as e:
        await update.message.reply_text(f"Error executing command: {e.output.decode('utf-8')}")
