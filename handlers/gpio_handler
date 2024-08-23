from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_gpio_status

async def gpio_command(update: Update, context: CallbackContext) -> None:
    gpio_status = get_gpio_status()
    await update.message.reply_text(gpio_status)
