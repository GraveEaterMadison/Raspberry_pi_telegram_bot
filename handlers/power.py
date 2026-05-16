"""handlers/power.py — Reboot, shutdown, and service management."""

import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


async def reboot_command(update: Update, context: CallbackContext) -> None:
    keyboard = [[
        InlineKeyboardButton("✅ Yes, reboot now!", callback_data="power:reboot"),
        InlineKeyboardButton("❌ Cancel",           callback_data="power:cancel"),
    ]]
    await update.message.reply_text(
        "⚠️ *Are you sure you want to reboot?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def shutdown_command(update: Update, context: CallbackContext) -> None:
    keyboard = [[
        InlineKeyboardButton("✅ Yes, shutdown!",  callback_data="power:shutdown"),
        InlineKeyboardButton("❌ Cancel",          callback_data="power:cancel"),
    ]]
    await update.message.reply_text(
        "⚠️ *Are you sure you want to shutdown?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def service_command(update: Update, context: CallbackContext) -> None:
    """Control a systemd service. Usage: /service <name> <start|stop|restart|status>"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/service <name> <start|stop|restart|status|enable|disable>`",
            parse_mode="Markdown",
        )
        return

    name   = context.args[0]
    action = context.args[1].lower()
    allowed = {"start", "stop", "restart", "status", "enable", "disable"}

    if action not in allowed:
        await update.message.reply_text(f"❌ Action must be one of: {', '.join(allowed)}")
        return

    # Sanitize service name
    import re
    if not re.match(r'^[a-zA-Z0-9_\-.]+$', name):
        await update.message.reply_text("❌ Invalid service name.")
        return

    msg = await update.message.reply_text(f"⚙️ Running `systemctl {action} {name}`...",
                                           parse_mode="Markdown")
    proc = await asyncio.create_subprocess_exec(
        "sudo", "systemctl", action, name,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    output = (stdout + stderr).decode().strip()

    if action == "status":
        await msg.edit_text(
            f"⚙️ *{name}* status:\n```\n{output[:3000]}\n```",
            parse_mode="Markdown",
        )
    else:
        icon = "✅" if proc.returncode == 0 else "❌"
        await msg.edit_text(
            f"{icon} `systemctl {action} {name}` returned code `{proc.returncode}`"
            + (f"\n```\n{output[:1000]}\n```" if output else ""),
            parse_mode="Markdown",
        )


async def services_command(update: Update, context: CallbackContext) -> None:
    """List active running services."""
    msg = await update.message.reply_text("📋 Fetching active services...")
    proc = await asyncio.create_subprocess_exec(
        "systemctl", "list-units", "--type=service", "--state=running",
        "--no-pager", "--no-legend",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    lines = stdout.decode().strip().splitlines()

    services = []
    for line in lines:
        parts = line.split()
        if parts:
            services.append(parts[0].replace(".service", ""))

    if not services:
        await msg.edit_text("No running services found (may need elevated permissions).")
        return

    chunks = [services[i:i+20] for i in range(0, len(services), 20)]
    result = (
        f"📋 *Running Services* ({len(services)} total)\n\n"
        + "\n".join(f"• `{s}`" for s in chunks[0])
    )
    if len(chunks) > 1:
        result += f"\n\n_...and {len(services) - 20} more_"

    await msg.edit_text(result, parse_mode="Markdown")
