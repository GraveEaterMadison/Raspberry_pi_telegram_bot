"""handlers/system.py — System monitoring commands."""

import logging
import platform
import subprocess
from datetime import datetime, timedelta

import psutil
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


def _temp() -> str:
    try:
        temps = psutil.sensors_temperatures()
        for key in ("cpu_thermal", "coretemp", "k10temp"):
            if key in temps:
                t = temps[key][0].current
                return f"{t:.1f}°C"
    except Exception:
        pass
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return f"{int(f.read()) / 1000:.1f}°C"
    except Exception:
        return "N/A"


async def info_command(update: Update, context: CallbackContext) -> None:
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot
    cpu_freq = psutil.cpu_freq()
    freq_str = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"

    uname = platform.uname()
    text = (
        "ℹ️ *System Information*\n\n"
        f"🖥️ *Host:*     `{uname.node}`\n"
        f"🐧 *OS:*       `{uname.system} {uname.release}`\n"
        f"🏗️ *Arch:*     `{uname.machine}`\n"
        f"🐍 *Python:*   `{platform.python_version()}`\n"
        f"⏱️ *Uptime:*   `{str(uptime).split('.')[0]}`\n"
        f"🖥️ *CPU:*      `{psutil.cpu_percent(0.5):.1f}%` @ `{freq_str}`\n"
        f"🧠 *RAM:*      `{mem.percent:.1f}%` ({mem.used>>20}/{mem.total>>20} MB)\n"
        f"💽 *Disk:*     `{disk.percent:.1f}%` ({disk.used>>30}/{disk.total>>30} GB)\n"
        f"🌡️ *Temp:*     `{_temp()}`\n"
        f"🔧 *Cores:*    `{psutil.cpu_count(logical=False)}` physical, `{psutil.cpu_count()}` logical\n"
        f"🕐 *Boot:*     `{boot.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cpu_command(update: Update, context: CallbackContext) -> None:
    percent = psutil.cpu_percent(interval=1, percpu=True)
    freq = psutil.cpu_freq()
    load = psutil.getloadavg()

    bars = []
    for i, p in enumerate(percent):
        filled = int(p / 10)
        bar = "█" * filled + "░" * (10 - filled)
        bars.append(f"  Core {i}: [{bar}] {p:.1f}%")

    freq_str = (
        f"Current: `{freq.current:.0f}` / Max: `{freq.max:.0f}` MHz"
        if freq else "N/A"
    )

    text = (
        "🖥️ *CPU Usage*\n\n"
        + "\n".join(f"`{b}`" for b in bars)
        + f"\n\n📊 *Load avg (1/5/15 min):* `{load[0]:.2f}` / `{load[1]:.2f}` / `{load[2]:.2f}`"
        + f"\n⚡ *Frequency:* {freq_str}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def ram_command(update: Update, context: CallbackContext) -> None:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    filled = int(mem.percent / 10)
    bar = "█" * filled + "░" * (10 - filled)

    text = (
        "🧠 *RAM Usage*\n\n"
        f"[`{bar}`] `{mem.percent:.1f}%`\n\n"
        f"📦 *Total:*     `{mem.total >> 20:,} MB`\n"
        f"✅ *Used:*      `{mem.used >> 20:,} MB`\n"
        f"🆓 *Available:* `{mem.available >> 20:,} MB`\n"
        f"🔄 *Cached:*    `{mem.cached >> 20:,} MB`\n\n"
        f"💾 *Swap:* `{swap.used >> 20:,} / {swap.total >> 20:,} MB` ({swap.percent:.1f}%)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def disk_command(update: Update, context: CallbackContext) -> None:
    lines = ["💽 *Disk Usage*\n"]
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            filled = int(usage.percent / 10)
            bar = "█" * filled + "░" * (10 - filled)
            lines.append(
                f"*{part.mountpoint}* (`{part.fstype}`)\n"
                f"[`{bar}`] `{usage.percent:.1f}%`\n"
                f"  `{usage.used >> 30:.1f} / {usage.total >> 30:.1f} GB`\n"
            )
        except PermissionError:
            continue
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def uptime_command(update: Update, context: CallbackContext) -> None:
    boot = datetime.fromtimestamp(psutil.boot_time())
    delta = datetime.now() - boot
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    mins, secs = divmod(rem, 60)
    await update.message.reply_text(
        f"⏱️ *System Uptime*\n\n"
        f"`{days}d {hours:02d}h {mins:02d}m {secs:02d}s`\n\n"
        f"🕐 *Booted:* `{boot.strftime('%Y-%m-%d %H:%M:%S')}`",
        parse_mode="Markdown",
    )


async def temperature_command(update: Update, context: CallbackContext) -> None:
    t = _temp()
    try:
        val = float(t.replace("°C", ""))
        if val >= 80:
            icon = "🔴"
            status = "CRITICAL — throttling may occur!"
        elif val >= 70:
            icon = "🟠"
            status = "Hot — consider improving cooling"
        elif val >= 60:
            icon = "🟡"
            status = "Warm but acceptable"
        else:
            icon = "🟢"
            status = "Normal"
    except ValueError:
        icon, status = "⚪", "Unknown"

    await update.message.reply_text(
        f"🌡️ *CPU Temperature*\n\n{icon} `{t}` — {status}",
        parse_mode="Markdown",
    )


async def healthscore_command(update: Update, context: CallbackContext) -> None:
    """Calculate an overall Pi health score 0-100."""
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent

    temp_val = None
    try:
        raw = _temp()
        temp_val = float(raw.replace("°C", ""))
    except ValueError:
        pass

    # Scoring (lower usage = better, lower temp = better)
    cpu_score  = max(0, 100 - cpu)
    ram_score  = max(0, 100 - mem)
    disk_score = max(0, 100 - disk)
    temp_score = max(0, 100 - max(0, (temp_val or 50) - 40) * 3) if temp_val else 75

    overall = (cpu_score + ram_score + disk_score + temp_score) / 4

    def grade(s):
        if s >= 90: return "🟢 Excellent"
        if s >= 70: return "🟡 Good"
        if s >= 50: return "🟠 Fair"
        return "🔴 Poor"

    await update.message.reply_text(
        f"💊 *Pi Health Score*\n\n"
        f"🖥️ CPU score:   `{cpu_score:.0f}/100`\n"
        f"🧠 RAM score:   `{ram_score:.0f}/100`\n"
        f"💽 Disk score:  `{disk_score:.0f}/100`\n"
        f"🌡️ Temp score:  `{temp_score:.0f}/100`\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 *Overall:* `{overall:.0f}/100` — {grade(overall)}",
        parse_mode="Markdown",
    )
