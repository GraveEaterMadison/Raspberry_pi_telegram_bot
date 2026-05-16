"""handlers/sysstat_handler.py — Combined system status: uptime, load, CPU, RAM.

Replaces the fork's thin wrapper with a formatted, emoji-rich summary that
pulls data directly from psutil (no subprocess, no locale issues).
"""

import logging
from datetime import datetime

import psutil
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


def _load_bar(load: float, cores: int) -> str:
    """Visual bar scaled to number of CPU cores (100% = all cores pegged)."""
    pct = min(1.0, load / max(cores, 1))
    filled = int(pct * 10)
    return "█" * filled + "░" * (10 - filled)


async def sysstat_command(update: Update, context: CallbackContext) -> None:
    """Compact system status snapshot: uptime, load averages, CPU, RAM."""
    cores = psutil.cpu_count(logical=True) or 1

    # Uptime
    boot  = datetime.fromtimestamp(psutil.boot_time())
    delta = datetime.now() - boot
    days  = delta.days
    h, r  = divmod(delta.seconds, 3600)
    m, s  = divmod(r, 60)
    uptime_str = f"{days}d {h:02d}h {m:02d}m {s:02d}s"

    # Load averages
    load1, load5, load15 = psutil.getloadavg()
    bar1  = _load_bar(load1,  cores)
    bar5  = _load_bar(load5,  cores)
    bar15 = _load_bar(load15, cores)

    # Load health indicator
    if load1 / cores >= 1.5:
        load_icon = "🔴"
    elif load1 / cores >= 0.8:
        load_icon = "🟠"
    else:
        load_icon = "🟢"

    # CPU
    cpu_pct   = psutil.cpu_percent(interval=0.5)
    cpu_freq  = psutil.cpu_freq()
    freq_str  = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"
    cpu_bar   = "█" * int(cpu_pct / 10) + "░" * (10 - int(cpu_pct / 10))
    cpu_icon  = "🔴" if cpu_pct >= 90 else "🟠" if cpu_pct >= 70 else "🟢"

    # RAM
    mem      = psutil.virtual_memory()
    ram_bar  = "█" * int(mem.percent / 10) + "░" * (10 - int(mem.percent / 10))
    ram_icon = "🔴" if mem.percent >= 90 else "🟠" if mem.percent >= 75 else "🟢"

    # Swap
    swap = psutil.swap_memory()
    swap_str = f"{swap.used >> 20:,} / {swap.total >> 20:,} MB ({swap.percent:.0f}%)" \
               if swap.total > 0 else "not configured"

    text = (
        "📊 *System Status*\n\n"
        f"⏱️ *Uptime:*   `{uptime_str}`\n"
        f"🕐 *Booted:*  `{boot.strftime('%Y-%m-%d %H:%M')}`\n\n"
        f"{load_icon} *Load avg (1/5/15 min):*\n"
        f"  1m:  [`{bar1}`]  `{load1:.2f}`\n"
        f"  5m:  [`{bar5}`]  `{load5:.2f}`\n"
        f"  15m: [`{bar15}`] `{load15:.2f}`\n"
        f"  _(cores: {cores})_\n\n"
        f"{cpu_icon} *CPU:* [`{cpu_bar}`] `{cpu_pct:.1f}%` @ `{freq_str}`\n\n"
        f"{ram_icon} *RAM:* [`{ram_bar}`] `{mem.percent:.1f}%`\n"
        f"  Used: `{mem.used >> 20:,} MB` / Total: `{mem.total >> 20:,} MB`\n"
        f"  Available: `{mem.available >> 20:,} MB`\n\n"
        f"💾 *Swap:* `{swap_str}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def loadavg_command(update: Update, context: CallbackContext) -> None:
    """Show load averages with context (number of cores)."""
    cores = psutil.cpu_count(logical=True) or 1
    load1, load5, load15 = psutil.getloadavg()

    def _status(load):
        ratio = load / cores
        if ratio >= 1.5:  return "🔴 overloaded"
        if ratio >= 0.8:  return "🟠 high"
        if ratio >= 0.4:  return "🟡 moderate"
        return "🟢 low"

    text = (
        f"📉 *Load Averages* (cores: `{cores}`)\n\n"
        f"  1 min:  `{load1:.2f}` — {_status(load1)}\n"
        f"  5 min:  `{load5:.2f}` — {_status(load5)}\n"
        f"  15 min: `{load15:.2f}` — {_status(load15)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
