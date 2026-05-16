import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


async def callback_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    prefix, _, action = data.partition(":")

    # ── Dashboard callbacks ───────────────────────────────────────────────────
    if prefix == "dash":
        import psutil
        from datetime import datetime

        if action == "cpu":
            percent = psutil.cpu_percent(interval=1, percpu=True)
            bars = [f"Core {i}: {'█'*int(p/10)}{'░'*(10-int(p/10))} {p:.1f}%" for i, p in enumerate(percent)]
            await query.edit_message_text(
                "🖥️ *CPU Usage*\n\n" + "\n".join(f"`{b}`" for b in bars),
                parse_mode="Markdown",
                reply_markup=_back_keyboard(),
            )

        elif action == "ram":
            m = psutil.virtual_memory()
            bar = "█" * int(m.percent / 10) + "░" * (10 - int(m.percent / 10))
            await query.edit_message_text(
                f"🧠 *RAM* [`{bar}`] `{m.percent:.1f}%`\n`{m.used>>20}/{m.total>>20} MB`",
                parse_mode="Markdown",
                reply_markup=_back_keyboard(),
            )

        elif action == "disk":
            disk = psutil.disk_usage("/")
            bar = "█" * int(disk.percent / 10) + "░" * (10 - int(disk.percent / 10))
            await query.edit_message_text(
                f"💽 *Disk* [`{bar}`] `{disk.percent:.1f}%`\n`{disk.used>>30:.1f}/{disk.total>>30:.1f} GB`",
                parse_mode="Markdown",
                reply_markup=_back_keyboard(),
            )

        elif action == "temp":
            t = _read_temp()
            icon = "🔴" if t > 75 else "🟡" if t > 60 else "🟢"
            await query.edit_message_text(
                f"🌡️ *CPU Temperature*\n\n{icon} `{t:.1f}°C`",
                parse_mode="Markdown",
                reply_markup=_back_keyboard(),
            )

        elif action == "uptime":
            boot = datetime.fromtimestamp(psutil.boot_time())
            delta = datetime.now() - boot
            h, r = divmod(delta.seconds, 3600)
            m, s = divmod(r, 60)
            await query.edit_message_text(
                f"⏱️ *Uptime:* `{delta.days}d {h:02d}h {m:02d}m {s:02d}s`",
                parse_mode="Markdown",
                reply_markup=_back_keyboard(),
            )

        elif action == "health":
            cpu  = psutil.cpu_percent(interval=1)
            ram  = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            temp = _read_temp()
            score = (max(0,100-cpu)+max(0,100-ram)+max(0,100-disk)+max(0,100-max(0,temp-40)*3))/4
            grade = "🟢 Excellent" if score>=90 else "🟡 Good" if score>=70 else "🟠 Fair" if score>=50 else "🔴 Poor"
            await query.edit_message_text(
                f"💊 *Health Score*\n\n"
                f"CPU `{100-cpu:.0f}` RAM `{100-ram:.0f}` Disk `{100-disk:.0f}` Temp `{max(0,100-max(0,temp-40)*3):.0f}`\n\n"
                f"🏆 *{score:.0f}/100* — {grade}",
                parse_mode="Markdown",
                reply_markup=_back_keyboard(),
            )

        elif action == "ip":
            import socket
            lines = []
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        lines.append(f"• `{iface}`: `{addr.address}`")
            await query.edit_message_text(
                "🌐 *IP Addresses*\n\n" + ("\n".join(lines) or "None"),
                parse_mode="Markdown",
                reply_markup=_back_keyboard(),
            )

        elif action == "wifi":
            await query.edit_message_text("📶 Use `/wifi` to scan networks.", parse_mode="Markdown", reply_markup=_back_keyboard())

        elif action.startswith("graph_"):
            metric = action.split("_")[1]
            await query.edit_message_text(f"📊 Run `/graph {metric}` to generate a chart.", parse_mode="Markdown", reply_markup=_back_keyboard())

        elif action == "snapshot":
            await query.edit_message_text("📸 Run `/snapshot` to capture a photo.", parse_mode="Markdown", reply_markup=_back_keyboard())

        elif action == "reboot_confirm":
            keyboard = [[
                InlineKeyboardButton("✅ CONFIRM REBOOT", callback_data="power:reboot"),
                InlineKeyboardButton("❌ Cancel",         callback_data="dash:refresh"),
            ]]
            await query.edit_message_text(
                "⚠️ *Confirm reboot?*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        elif action == "shutdown_confirm":
            keyboard = [[
                InlineKeyboardButton("✅ CONFIRM SHUTDOWN", callback_data="power:shutdown"),
                InlineKeyboardButton("❌ Cancel",           callback_data="dash:refresh"),
            ]]
            await query.edit_message_text(
                "⚠️ *Confirm shutdown?*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

        elif action == "refresh":
            keyboard = [
                [InlineKeyboardButton("🖥️ CPU", callback_data="dash:cpu"),
                 InlineKeyboardButton("🧠 RAM", callback_data="dash:ram"),
                 InlineKeyboardButton("💽 Disk", callback_data="dash:disk")],
                [InlineKeyboardButton("🌡️ Temp", callback_data="dash:temp"),
                 InlineKeyboardButton("⏱️ Uptime", callback_data="dash:uptime"),
                 InlineKeyboardButton("💊 Health", callback_data="dash:health")],
                [InlineKeyboardButton("📸 Snapshot", callback_data="dash:snapshot"),
                 InlineKeyboardButton("🌐 IP", callback_data="dash:ip"),
                 InlineKeyboardButton("📡 WiFi", callback_data="dash:wifi")],
                [InlineKeyboardButton("📊 Graph CPU", callback_data="dash:graph_cpu"),
                 InlineKeyboardButton("📊 Graph RAM", callback_data="dash:graph_ram"),
                 InlineKeyboardButton("📊 Graph Temp", callback_data="dash:graph_temp")],
                [InlineKeyboardButton("🔄 Reboot", callback_data="dash:reboot_confirm"),
                 InlineKeyboardButton("⚡ Shutdown", callback_data="dash:shutdown_confirm"),
                 InlineKeyboardButton("🔁 Refresh", callback_data="dash:refresh")],
            ]
            await query.edit_message_text(
                "🎛️ *Raspberry Pi Control Panel*\n\nSelect an action:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )

    # ── Power callbacks ───────────────────────────────────────────────────────
    elif prefix == "power":
        if action == "reboot":
            await query.edit_message_text("🔄 *Rebooting...* Goodbye! 👋", parse_mode="Markdown")
            await asyncio.create_subprocess_exec("sudo", "reboot")
        elif action == "shutdown":
            await query.edit_message_text("⚡ *Shutting down...* Goodbye! 👋", parse_mode="Markdown")
            await asyncio.create_subprocess_exec("sudo", "shutdown", "now")
        elif action == "cancel":
            await query.edit_message_text("✅ Action cancelled.")


def _back_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="dash:refresh")
    ]])


def _read_temp() -> float:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read()) / 1000.0
    except Exception:
        return 0.0
