"""handlers/exec_handler.py — Remote shell execution with safety checks."""

import asyncio
import logging
from telegram import Update
from telegram.ext import CallbackContext
from config import MAX_EXEC_OUTPUT, EXEC_BLACKLIST, EXEC_WHITELIST

logger = logging.getLogger(__name__)


async def exec_command(update: Update, context: CallbackContext) -> None:
    """Run a shell command. Usage: /exec <command>"""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/exec <shell command>`\nExample: `/exec ls -la /home/pi`",
            parse_mode="Markdown",
        )
        return

    cmd = " ".join(context.args)

    # Safety: block blacklisted commands
    for blocked in EXEC_BLACKLIST:
        if blocked.lower() in cmd.lower():
            await update.message.reply_text(
                f"🚫 Command blocked by security policy.\nBlacklisted pattern: `{blocked}`",
                parse_mode="Markdown",
            )
            logger.warning("Blocked exec attempt: %s", cmd)
            return

    # Optional whitelist mode
    if EXEC_WHITELIST:
        base_cmd = cmd.split()[0]
        if base_cmd not in EXEC_WHITELIST:
            await update.message.reply_text(
                f"🚫 `{base_cmd}` is not in the allowed commands list.",
                parse_mode="Markdown",
            )
            return

    msg = await update.message.reply_text(f"💻 Running:\n```\n{cmd}\n```",
                                           parse_mode="Markdown")
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stdout.decode(errors="replace").strip()

        if len(output) > MAX_EXEC_OUTPUT:
            output = output[-MAX_EXEC_OUTPUT:]
            prefix = "⚠️ _Output truncated (showing last portion)_\n\n"
        else:
            prefix = ""

        result = (
            f"💻 *Command:* `{cmd}`\n"
            f"↩️ *Exit code:* `{proc.returncode}`\n\n"
            f"{prefix}```\n{output or '(no output)'}\n```"
        )
        await msg.edit_text(result, parse_mode="Markdown")

    except asyncio.TimeoutError:
        proc.kill()
        await msg.edit_text(f"⏰ Command timed out after 30 seconds.\n`{cmd}`",
                            parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Error: `{e}`", parse_mode="Markdown")
