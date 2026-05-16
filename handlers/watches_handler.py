"""handlers/watches_handler.py — Bluetooth smartwatch health-check via IPC.

Sends a health-check message to one or more Bluetooth watches through the
watch_notifier IPC socket daemon. The MAC addresses of paired watches are
read from the env var WATCH_ADDRESSES (comma-separated) or the .env file,
so no hardcoded MACs live in source code.

Usage:
  /watches           → ping all configured watches
  /watches <mac>     → ping a specific MAC address
"""

import asyncio
import logging
import os
import re

from telegram import Update
from telegram.ext import CallbackContext
from utils.watch_notifier_ipc import send_bt_message_async

logger = logging.getLogger(__name__)

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def _configured_macs() -> list[str]:
    """Read WATCH_ADDRESSES from environment; return validated MAC list."""
    raw = os.getenv("WATCH_ADDRESSES", "")
    macs = [m.strip() for m in raw.split(",") if m.strip()]
    valid = [m.upper() for m in macs if _MAC_RE.match(m)]
    if len(valid) != len(macs):
        invalid = [m for m in macs if not _MAC_RE.match(m)]
        logger.warning("Ignored invalid MACs in WATCH_ADDRESSES: %s", invalid)
    return valid


async def watches_command(update: Update, context: CallbackContext) -> None:
    """Ping Bluetooth watches to verify IPC connectivity."""
    # Allow one-off MAC from args: /watches 2C:BC:BB:A7:DE:3A
    if context.args and _MAC_RE.match(context.args[0]):
        targets = [context.args[0].upper()]
    else:
        targets = _configured_macs()

    if not targets:
        await update.message.reply_text(
            "❌ No watch addresses configured.\n"
            "Set `WATCH_ADDRESSES=AA:BB:CC:DD:EE:FF` in your `.env` file, "
            "or pass a MAC directly: `/watches AA:BB:CC:DD:EE:FF`",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text(
        f"🔵 Sending health-check to {len(targets)} watch(es)..."
    )

    ok, failed = [], []
    for mac in targets:
        success = await send_bt_message_async(mac, "Health check")
        (ok if success else failed).append(mac)

    lines = [f"🔵 *Watch Health Check* ({len(targets)} target(s))\n"]
    for mac in ok:
        lines.append(f"  ✅ `{mac}` — reachable")
    for mac in failed:
        lines.append(f"  ❌ `{mac}` — no response")

    if failed:
        lines.append(
            "\n⚠️ Failed watches may be out of range, powered off, "
            "or the `watch_notifier` daemon is not running."
        )
    else:
        lines.append(f"\n✅ All {len(ok)} watch(es) responded successfully.")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown")
