import logging
import asyncio
import signal
import sys
import os
from functools import partial

os.makedirs("data", exist_ok=True)

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

from config import API_TOKEN, LOG_LEVEL
from utils.auth import require_auth
from utils.logger import AuditLogger
from utils.metrics import MetricsCollector

# ── Handlers ─────────────────────────────────────────────────────────────────
from handlers.core import start_command, help_command, dashboard_command
from handlers.system import (
    info_command, cpu_command, ram_command, disk_command,
    uptime_command, temperature_command, healthscore_command,
)
from handlers.network import (
    ip_command, netinfo_command, ping_command,
    wifi_command, speedtest_command, portscan_command,
)
from handlers.power import (
    reboot_command, shutdown_command,
    service_command, services_command,
)
from handlers.exec_handler import exec_command
from handlers.files import ls_command, cat_command, download_command, upload_handler
from handlers.gpio_handler import gpio_command, pwm_command, servo_command, i2c_command
from handlers.camera import snapshot_command, motion_command
from handlers.monitoring import graph_command, alert_command, metrics_command
from handlers.ai_handler import ai_command
from handlers.scheduler import schedule_command, cron_command
from handlers.notes import note_command
from handlers.packages import pkg_command
from handlers.backup import backup_command
from handlers.weather import weather_command
from handlers.sensors import sensors_command
from handlers.process import ps_command, kill_command
from handlers.callbacks import callback_handler

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("ultra_pi_bot")

# ── Global singletons ─────────────────────────────────────────────────────────
audit = AuditLogger()
metrics = MetricsCollector()


def auth(fn):
    """Shortcut: wrap a handler with authorization check."""
    return partial(require_auth, handler=fn, audit=audit)


# ── Bot commands registration ─────────────────────────────────────────────────
COMMANDS = [
    # (command, handler_fn, description, requires_auth)
    ("start",       start_command,       "👋 Welcome message",                  False),
    ("help",        help_command,        "📖 List all commands",                False),
    ("dashboard",   dashboard_command,   "🎛️  Interactive control panel",       True),

    # System
    ("info",        info_command,        "ℹ️  Full system info",                True),
    ("cpu",         cpu_command,         "🖥️  CPU usage & frequency",           True),
    ("ram",         ram_command,         "🧠 RAM usage",                        True),
    ("disk",        disk_command,        "💽 Disk space",                       True),
    ("uptime",      uptime_command,      "⏱️  System uptime",                   True),
    ("temperature", temperature_command, "🌡️  CPU temperature",                 True),
    ("healthscore", healthscore_command, "💊 Overall Pi health score",          True),

    # Network
    ("ip",          ip_command,          "🌐 IP addresses",                     True),
    ("netinfo",     netinfo_command,     "📡 Network interfaces",               True),
    ("ping",        ping_command,        "🏓 Ping a host",                      True),
    ("wifi",        wifi_command,        "📶 Scan WiFi networks",               True),
    ("speedtest",   speedtest_command,   "🚀 Internet speed test",              True),
    ("portscan",    portscan_command,    "🔍 Scan ports on a host",             True),

    # Power & Services
    ("reboot",      reboot_command,      "🔄 Reboot the Pi",                    True),
    ("shutdown",    shutdown_command,    "⚡ Shutdown the Pi",                  True),
    ("service",     service_command,     "⚙️  Control a systemd service",        True),
    ("services",    services_command,    "📋 List running services",            True),

    # Remote Execution
    ("exec",        exec_command,        "💻 Execute a shell command",          True),

    # Files
    ("ls",          ls_command,          "📂 List directory",                   True),
    ("cat",         cat_command,         "📄 Read a file",                      True),
    ("download",    download_command,    "⬇️  Download file from Pi",            True),

    # GPIO
    ("gpio",        gpio_command,        "🔌 GPIO on/off control",              True),
    ("pwm",         pwm_command,         "〰️  PWM control",                     True),
    ("servo",       servo_command,       "🦾 Servo motor control",              True),
    ("i2c",         i2c_command,         "🔎 I2C device scanner",               True),

    # Camera
    ("snapshot",    snapshot_command,    "📸 Capture camera photo",             True),
    ("motion",      motion_command,      "🚨 Toggle motion detection",          True),

    # Monitoring
    ("graph",       graph_command,       "📊 Plot CPU/RAM/temp graph",          True),
    ("alert",       alert_command,       "🔔 Set/list/clear resource alerts",   True),
    ("metrics",     metrics_command,     "📈 Recent metrics history",           True),

    # AI
    ("ai",          ai_command,          "🤖 Ask AI a question",                True),

    # Scheduler
    ("schedule",    schedule_command,    "📅 Schedule a command",               True),
    ("cron",        cron_command,        "🗓️  Manage cron jobs",                 True),

    # Notes
    ("note",        note_command,        "📝 Notes & reminders",                True),

    # Packages
    ("pkg",         pkg_command,         "📦 APT package manager",              True),

    # Backup
    ("backup",      backup_command,      "💾 Backup & download files",          True),

    # Weather
    ("weather",     weather_command,     "🌍 Weather at Pi's location",         True),

    # Sensors
    ("sensors",     sensors_command,     "🌡️  Read connected sensors",           True),

    # Processes
    ("ps",          ps_command,          "🔎 List running processes",           True),
    ("kill",        kill_command,        "💀 Kill a process by PID",            True),
]


async def post_init(application: Application) -> None:
    """Set bot commands menu and start background tasks."""
    await application.bot.set_my_commands([
        BotCommand(cmd, desc)
        for cmd, _, desc, _ in COMMANDS
    ])

    # Wire the alert notifier: when metrics fires an alert, send a Telegram message
    async def _alert_notifier(user_id: int, text: str):
        try:
            await application.bot.send_message(user_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.error("Alert notify failed: %s", e)

    metrics.set_notifier(_alert_notifier)

    # Give the monitoring handler access to the global metrics instance
    from handlers import monitoring as mon_module
    mon_module.set_metrics(metrics)

    # Start background metrics collection loop
    asyncio.create_task(metrics.collect_loop())

    # Start scheduled-task runner
    from handlers.scheduler import scheduler_loop
    asyncio.create_task(scheduler_loop(application.bot))

    logger.info("🚀 Ultra Pi Bot started — %d commands registered", len(COMMANDS))


async def error_handler(update: object, context: CallbackContext) -> None:
    """Global error handler — logs and notifies user."""
    logger.error("Unhandled exception", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"⚠️ An unexpected error occurred:\n`{type(context.error).__name__}: {context.error}`",
                parse_mode="Markdown",
            )
        except Exception:
            pass


def main() -> None:
    audit.init()
    metrics.init()

    application = (
        ApplicationBuilder()
        .token(API_TOKEN)
        .post_init(post_init)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # Register all commands
    for cmd, handler_fn, _desc, protected in COMMANDS:
        if protected:
            wrapped = auth(handler_fn)
        else:
            wrapped = handler_fn
        application.add_handler(CommandHandler(cmd, wrapped))
        
    application.add_handler(
        MessageHandler(filters.Document.ALL, auth(upload_handler))
    )

    # Inline keyboard callback handler
    application.add_handler(CallbackQueryHandler(callback_handler))

    # Global error handler
    application.add_error_handler(error_handler)

    # Graceful shutdown on SIGTERM/SIGINT
    def _shutdown(*_):
        logger.info("Shutdown signal received")
        application.stop_running()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("🤖 Starting bot polling...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
