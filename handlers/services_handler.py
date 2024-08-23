from telegram import Update
from telegram.ext import CallbackContext
from utils.pi_info import get_running_services, get_all_services

async def send_long_message(chat_id, text, bot):
    # Split the text into chunks of 4096 characters
    chunk_size = 4096
    for i in range(0, len(text), chunk_size):
        await bot.send_message(chat_id=chat_id, text=text[i:i+chunk_size])

async def services_command(update: Update, context: CallbackContext) -> None:
    args = context.args
    if not args or args[0] not in ["running", "all"]:
        await update.message.reply_text("Usage: /services <running|all>")
        return

    if args[0] == "running":
        services = get_running_services()
    else:  # args[0] == "all"
        services = get_all_services()

    if len(services) > 4096:
        await send_long_message(update.effective_chat.id, services, context.bot)
    else:
        await update.message.reply_text(services)
