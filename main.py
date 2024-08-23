import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from config import API_TOKEN
from utils.auth import check_authorization
from handlers.help_handler import help_command
from handlers.info_handler import info_command
from handlers.temp_handler import temperature_command
from handlers.ip_handler import ip_command
from handlers.ram_handler import ram_command
from handlers.cpu_handler import cpu_command
from handlers.disk_handler import disk_command
from handlers.uptime_handler import uptime_command
from handlers.exec_handler import exec_command_handler
from handlers.shutdown_handler import shutdown_command
from handlers.reboot_handler import reboot_command
from handlers.service_handler import service_command
from handlers.gpio_handler import gpio_command
from handlers.netinfo_handler import netinfo_command
from handlers.ping_handler import ping_command
from handlers.services_handler import services_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Welcome to Raspberry Pi Controller Bot!")

async def handle_command(update: Update, context: CallbackContext, command_handler):
    """Wrapper to check authorization before calling the command handler."""
    await check_authorization(update, context, command_handler)

def main() -> None:
    application = Application.builder().token(API_TOKEN).build()

    application.add_handler(CommandHandler("start", lambda update, context: handle_command(update, context, start)))
    application.add_handler(CommandHandler("help", lambda update, context: handle_command(update, context, help_command)))
    application.add_handler(CommandHandler("info", lambda update, context: handle_command(update, context, info_command)))
    application.add_handler(CommandHandler("temperature", lambda update, context: handle_command(update, context, temperature_command)))
    application.add_handler(CommandHandler("ip", lambda update, context: handle_command(update, context, ip_command)))
    application.add_handler(CommandHandler("ram", lambda update, context: handle_command(update, context, ram_command)))
    application.add_handler(CommandHandler("cpu", lambda update, context: handle_command(update, context, cpu_command)))
    application.add_handler(CommandHandler("disk", lambda update, context: handle_command(update, context, disk_command)))
    application.add_handler(CommandHandler("uptime", lambda update, context: handle_command(update, context, uptime_command)))
    application.add_handler(CommandHandler("exec", lambda update, context: handle_command(update, context, exec_command_handler)))
    application.add_handler(CommandHandler("shutdown", lambda update, context: handle_command(update, context, shutdown_command)))
    application.add_handler(CommandHandler("reboot", lambda update, context: handle_command(update, context, reboot_command)))
    application.add_handler(CommandHandler("service", lambda update, context: handle_command(update, context, service_command)))
    application.add_handler(CommandHandler("gpio", lambda update, context: handle_command(update, context, gpio_command)))
    application.add_handler(CommandHandler("netinfo", lambda update, context: handle_command(update, context, netinfo_command)))
    application.add_handler(CommandHandler("ping", lambda update, context: handle_command(update, context, ping_command)))
    application.add_handler(CommandHandler("services", lambda update, context: handle_command(update, context, services_command)))

    application.run_polling()

if __name__ == '__main__':
    main()
