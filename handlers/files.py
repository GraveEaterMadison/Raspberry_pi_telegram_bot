"""handlers/files.py — Remote file manager."""

import logging
import os
import stat
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

SAFE_ROOTS = ["/home", "/var/log", "/etc", "/tmp", "/opt"]
MAX_CAT_SIZE = 50_000   # 50 KB
MAX_SEND_SIZE = 50 * 1024 * 1024  # 50 MB


def _is_safe(path: str) -> bool:
    """Prevent directory traversal attacks."""
    resolved = os.path.realpath(path)
    return any(resolved.startswith(root) for root in SAFE_ROOTS)


async def ls_command(update: Update, context: CallbackContext) -> None:
    """List directory. Usage: /ls [path]"""
    target = " ".join(context.args) if context.args else "/home/pi"

    if not _is_safe(target):
        await update.message.reply_text(
            f"🚫 Access denied. Allowed roots: {', '.join(SAFE_ROOTS)}"
        )
        return

    try:
        entries = sorted(os.scandir(target), key=lambda e: (not e.is_dir(), e.name))
    except PermissionError:
        await update.message.reply_text(f"❌ Permission denied: `{target}`",
                                        parse_mode="Markdown")
        return
    except FileNotFoundError:
        await update.message.reply_text(f"❌ Not found: `{target}`", parse_mode="Markdown")
        return

    lines = [f"📂 *{target}/*\n"]
    for entry in entries[:50]:
        info = entry.stat(follow_symlinks=False)
        size = _human_size(info.st_size)
        mtime = datetime.fromtimestamp(info.st_mtime).strftime("%m-%d %H:%M")
        icon = "📁" if entry.is_dir() else "📄"
        perms = stat.filemode(info.st_mode)
        lines.append(f"{icon} `{perms}` `{size:>8}` `{mtime}` {entry.name}")

    if len(entries) > 50:
        lines.append(f"\n_...{len(entries) - 50} more entries_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def _human_size(n: int) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}T"


async def cat_command(update: Update, context: CallbackContext) -> None:
    """Read a file. Usage: /cat <path>"""
    if not context.args:
        await update.message.reply_text("Usage: `/cat <path>`", parse_mode="Markdown")
        return

    path = " ".join(context.args)
    if not _is_safe(path):
        await update.message.reply_text("🚫 Access denied.")
        return

    try:
        size = os.path.getsize(path)
        if size > MAX_CAT_SIZE:
            await update.message.reply_text(
                f"⚠️ File too large ({_human_size(size)}) to display inline. Use `/download {path}`.",
                parse_mode="Markdown",
            )
            return

        with open(path, "r", errors="replace") as f:
            content = f.read()

        chunks = [content[i:i+3500] for i in range(0, len(content), 3500)]
        for i, chunk in enumerate(chunks[:3]):
            header = f"📄 `{path}`" + (f" (part {i+1}/{len(chunks)})" if len(chunks) > 1 else "")
            await update.message.reply_text(
                f"{header}\n```\n{chunk}\n```", parse_mode="Markdown"
            )

    except PermissionError:
        await update.message.reply_text(f"❌ Permission denied: `{path}`",
                                        parse_mode="Markdown")
    except FileNotFoundError:
        await update.message.reply_text(f"❌ File not found: `{path}`",
                                        parse_mode="Markdown")


async def download_command(update: Update, context: CallbackContext) -> None:
    """Send a file to Telegram. Usage: /download <path>"""
    if not context.args:
        await update.message.reply_text("Usage: `/download <path>`", parse_mode="Markdown")
        return

    path = " ".join(context.args)
    if not _is_safe(path):
        await update.message.reply_text("🚫 Access denied.")
        return

    try:
        size = os.path.getsize(path)
    except (FileNotFoundError, PermissionError) as e:
        await update.message.reply_text(f"❌ {e}")
        return

    if size > MAX_SEND_SIZE:
        await update.message.reply_text(
            f"❌ File too large ({_human_size(size)}). Max: 50 MB."
        )
        return

    msg = await update.message.reply_text(f"⬇️ Sending `{path}`...", parse_mode="Markdown")
    try:
        with open(path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=os.path.basename(path),
                caption=f"📄 `{path}` ({_human_size(size)})",
                parse_mode="Markdown",
            )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Failed to send: `{e}`", parse_mode="Markdown")


async def upload_handler(update: Update, context: CallbackContext) -> None:
    """Handle file uploads from Telegram → Pi. Send a file as a reply to any message."""
    doc = update.message.document
    if not doc:
        return

    dest_dir = "/tmp/telegram_uploads"
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, doc.file_name)

    msg = await update.message.reply_text(f"⬆️ Uploading `{doc.file_name}`...",
                                           parse_mode="Markdown")
    try:
        file = await context.bot.get_file(doc.file_id)
        await file.download_to_drive(dest)
        await msg.edit_text(
            f"✅ File saved to `{dest}`\n"
            f"Size: `{_human_size(doc.file_size)}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        await msg.edit_text(f"❌ Upload failed: `{e}`", parse_mode="Markdown")
