"""handlers/backup.py — Backup files as tar.gz and send to Telegram."""
import asyncio
import logging
import os
import tarfile
import tempfile
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from config import BACKUP_PATHS

logger = logging.getLogger(__name__)
MAX_BACKUP_SIZE = 45 * 1024 * 1024  # 45 MB


_SAFE_ROOTS = ("/home", "/var/log", "/etc", "/tmp", "/opt")


def _is_safe_path(path: str) -> bool:
    resolved = os.path.realpath(path)
    return any(resolved.startswith(r) for r in _SAFE_ROOTS)


async def backup_command(update: Update, context: CallbackContext) -> None:
    paths = list(context.args) if context.args else BACKUP_PATHS

   
    valid = [p for p in paths if os.path.exists(p) and _is_safe_path(p)]
    unsafe = [p for p in paths if os.path.exists(p) and not _is_safe_path(p)]

    if unsafe:
        await update.message.reply_text(
            f"🚫 Access denied for path(s): `{', '.join(unsafe)}`\n"
            f"Allowed roots: `{', '.join(_SAFE_ROOTS)}`",
            parse_mode="Markdown",
        )
        return

    if not valid:
        await update.message.reply_text(
            f"❌ None of the specified paths exist: `{', '.join(paths)}`\n"
            f"Default backup paths: `{', '.join(BACKUP_PATHS)}`",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text(
        f"💾 Creating backup of: `{', '.join(valid)}`...", parse_mode="Markdown"
    )
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp = tempfile.NamedTemporaryFile(
        suffix=".tar.gz", prefix=f"pi_backup_{ts}_", delete=False
    )
    tmp.close()

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _create_tar, tmp.name, valid)
        size = os.path.getsize(tmp.name)

        if size > MAX_BACKUP_SIZE:
            await msg.edit_text(
                f"⚠️ Backup too large ({size >> 20} MB > 45 MB). "
                f"Specify smaller paths: `/backup /home/pi/.config`",
                parse_mode="Markdown",
            )
            return

        with open(tmp.name, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"pi_backup_{ts}.tar.gz",
                caption=(
                    f"💾 *Backup*\n"
                    f"Paths: `{', '.join(valid)}`\n"
                    f"Size: `{size >> 10:,} KB`"
                ),
                parse_mode="Markdown",
            )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Backup failed: `{e}`", parse_mode="Markdown")
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def _create_tar(output: str, paths: list):
    with tarfile.open(output, "w:gz") as tar:
        for path in paths:
            tar.add(path, recursive=True)
