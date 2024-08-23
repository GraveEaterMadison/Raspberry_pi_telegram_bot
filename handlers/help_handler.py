# handlers/help_handler.py
from telegram import Update
from telegram.ext import CallbackContext

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "/help - Show this help message\n\n"
        "/info - Get system information\n\n"
        "/temperature - Get CPU temperature\n\n"
        "/ip - Get IP addresses\n\n"
        "/ram - Get RAM usage\n\n"
        "/cpu - Get CPU usage\n\n"
        "/disk - Get disk usage\n\n"
        "/uptime - Get system uptime\n\n"
        "/exec - Execute a command\n\n"
        "/shutdown - Shutdown the system. use at for the exact time and in for countdown\n\n"
        "/reboot - Reboot the system. use at for the exact time and in for countdown\n\n"
        "/services - Show running or all services\n\n"
        "/service - Manage services\n\n"
        "/gpio - Get GPIO status\n\n"
        "/netinfo - Get network interfaces\n\n"
        "/ping - Ping a host\n\n"
    )
    await update.message.reply_text(help_text)
