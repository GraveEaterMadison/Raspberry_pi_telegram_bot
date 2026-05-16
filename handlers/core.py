"""handlers/core.py — Start, help, and interactive dashboard."""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

WELCOME_TEXT = """
🍓 *Ultra Raspberry Pi Bot v2.0*

Hello, {name}! Your Pi is online and ready.

Use /help to see all available commands, or /dashboard for the interactive control panel.
"""

HELP_TEXT = """
🍓 *Ultra Raspberry Pi Bot — Command Reference*

*📊 System Info*
/info          → Full system overview
/cpu           → CPU usage & frequency
/ram           → RAM usage
/disk          → Disk space
/uptime        → System uptime
/temperature   → CPU temperature
/healthscore   → Overall health score

*🌐 Network*
/ip            → IP addresses
/netinfo       → Network interfaces
/ping <host>   → Ping a host
/wifi          → Scan WiFi networks
/speedtest     → Internet speed test
/portscan <host> [range] → Scan ports

*⚙️ Power & Services*
/reboot        → Reboot the Pi
/shutdown      → Shutdown the Pi
/service <name> <start|stop|status|restart> → Manage a service
/services      → List running services

*💻 Remote Execution*
/exec <command> → Run a shell command
/ps            → List top processes
/kill <pid>    → Kill a process

*📁 Files*
/ls [path]     → List directory (default: /home/pi)
/cat <path>    → Read a file
/download <path> → Send file to Telegram
Upload a file (reply to /upload prompt) → Upload to Pi

*🔌 GPIO & Hardware*
/gpio <pin> <on|off>  → Digital GPIO control
/pwm <pin> <0-100>    → PWM duty cycle
/servo <pin> <0-180>  → Servo angle
/i2c           → Scan I2C bus
/sensors       → Read all sensors (DHT, BMP, PIR)

*📸 Camera*
/snapshot      → Take a photo
/motion <on|off> → Toggle motion detection

*📈 Monitoring*
/graph <cpu|ram|temp>  → Plot metric history
/alert set <cpu|ram|temp> <>>|<< threshold> → Set alert
/alert list    → List your alerts
/alert clear   → Clear all alerts
/metrics       → Recent metrics table

*🤖 AI Assistant*
/ai <question> → Ask the AI anything

*📅 Scheduler*
/schedule <HH:MM> <command> → Run command at time
/cron list     → Show cron jobs
/cron add <expr> <command> → Add cron job
/cron del <id> → Delete cron job

*📝 Notes*
/note add <text> → Add a note
/note list     → List notes
/note del <id> → Delete a note

*📦 Packages*
/pkg search <name>   → Search APT packages
/pkg install <name>  → Install a package
/pkg remove <name>   → Remove a package
/pkg update          → Update package list

*💾 Backup*
/backup [paths...] → Create & send tar.gz backup

*🌍 Misc*
/weather [city]  → Current weather
/dashboard       → Interactive control panel
/help            → This help message
"""


async def start_command(update: Update, context: CallbackContext) -> None:
    """Public welcome message — no auth required."""
    name = update.effective_user.first_name or "Hacker"
    await update.message.reply_text(
        WELCOME_TEXT.format(name=name),
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def dashboard_command(update: Update, context: CallbackContext) -> None:
    """Interactive control panel with inline keyboard buttons."""
    keyboard = [
        [
            InlineKeyboardButton("🖥️ CPU",       callback_data="dash:cpu"),
            InlineKeyboardButton("🧠 RAM",        callback_data="dash:ram"),
            InlineKeyboardButton("💽 Disk",       callback_data="dash:disk"),
        ],
        [
            InlineKeyboardButton("🌡️ Temp",       callback_data="dash:temp"),
            InlineKeyboardButton("⏱️ Uptime",     callback_data="dash:uptime"),
            InlineKeyboardButton("💊 Health",     callback_data="dash:health"),
        ],
        [
            InlineKeyboardButton("📸 Snapshot",   callback_data="dash:snapshot"),
            InlineKeyboardButton("🌐 IP",         callback_data="dash:ip"),
            InlineKeyboardButton("📡 WiFi",       callback_data="dash:wifi"),
        ],
        [
            InlineKeyboardButton("📊 Graph CPU",  callback_data="dash:graph_cpu"),
            InlineKeyboardButton("📊 Graph RAM",  callback_data="dash:graph_ram"),
            InlineKeyboardButton("📊 Graph Temp", callback_data="dash:graph_temp"),
        ],
        [
            InlineKeyboardButton("🔄 Reboot",     callback_data="dash:reboot_confirm"),
            InlineKeyboardButton("⚡ Shutdown",   callback_data="dash:shutdown_confirm"),
            InlineKeyboardButton("🔁 Refresh",    callback_data="dash:refresh"),
        ],
    ]
    await update.message.reply_text(
        "🎛️ *Raspberry Pi Control Panel*\n\nSelect an action:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
