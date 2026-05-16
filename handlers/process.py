"""handlers/process.py — Process manager: /ps and /kill."""
import asyncio
import logging
import psutil
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


async def ps_command(update: Update, context: CallbackContext) -> None:
    """Show top 20 processes by CPU usage."""
    procs = sorted(
        [p.info for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"])
         if p.info["cpu_percent"] is not None],
        key=lambda x: x["cpu_percent"] or 0, reverse=True
    )[:20]

    lines = [
        "🔎 *Top Processes*\n",
        "`PID    CPU%   MEM%  NAME`",
        "`─────────────────────────`",
    ]
    for p in procs:
        pid  = p["pid"]
        cpu  = p["cpu_percent"] or 0
        mem  = p["memory_percent"] or 0
        name = (p["name"] or "?")[:16]
        lines.append(f"`{pid:<6} {cpu:5.1f}  {mem:5.1f}  {name}`")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def kill_command(update: Update, context: CallbackContext) -> None:
    """Kill a process by PID. Usage: /kill <pid>"""
    if not context.args:
        await update.message.reply_text("Usage: `/kill <pid>`", parse_mode="Markdown")
        return
    try:
        pid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ PID must be a number.")
        return

    try:
        proc = psutil.Process(pid)
        name = proc.name()
        proc.terminate()
        await update.message.reply_text(
            f"✅ Sent SIGTERM to PID `{pid}` (`{name}`)", parse_mode="Markdown"
        )
    except psutil.NoSuchProcess:
        await update.message.reply_text(f"❌ No process with PID `{pid}`", parse_mode="Markdown")
    except psutil.AccessDenied:
        await update.message.reply_text(f"❌ Permission denied. Try running the bot with `sudo`.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode="Markdown")
