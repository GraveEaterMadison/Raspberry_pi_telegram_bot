"""handlers/packages.py — APT package manager wrapper."""
import asyncio
import logging
import re
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

SAFE_PKG_RE = re.compile(r'^[a-zA-Z0-9._\-]+$')


async def pkg_command(update: Update, context: CallbackContext) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage:\n`/pkg search <name>` — Search packages\n"
            "`/pkg install <name>` — Install package\n"
            "`/pkg remove <name>` — Remove package\n"
            "`/pkg update` — Update package list",
            parse_mode="Markdown",
        )
        return

    sub = args[0].lower()

    if sub == "update":
        msg = await update.message.reply_text("📦 Running `apt update`...")
        proc = await asyncio.create_subprocess_exec(
            "sudo", "apt", "update", "-y",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode()[-2000:]
        await msg.edit_text(f"📦 `apt update` done:\n```\n{output}\n```", parse_mode="Markdown")
        return

    if len(args) < 2:
        await update.message.reply_text("❌ Specify a package name.")
        return

    pkg = args[1]
    if not SAFE_PKG_RE.match(pkg):
        await update.message.reply_text("❌ Invalid package name.")
        return

    if sub == "search":
        msg = await update.message.reply_text(f"🔍 Searching for `{pkg}`...", parse_mode="Markdown")
        proc = await asyncio.create_subprocess_exec(
            "apt-cache", "search", pkg,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        stdout, _ = await proc.communicate()
        results = stdout.decode().strip().splitlines()[:15]
        if results:
            text = "\n".join(f"• `{r}`" for r in results)
            await msg.edit_text(f"🔍 Results for `{pkg}`:\n\n{text}", parse_mode="Markdown")
        else:
            await msg.edit_text(f"❌ No packages found matching `{pkg}`.", parse_mode="Markdown")

    elif sub in ("install", "remove"):
        cmd = ["sudo", "apt", sub if sub == "remove" else "install", "-y", pkg]
        msg = await update.message.reply_text(f"📦 Running `apt {sub} {pkg}`... (may take a while)", parse_mode="Markdown")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = stdout.decode()[-2000:]
            icon = "✅" if proc.returncode == 0 else "❌"
            await msg.edit_text(f"{icon} `apt {sub} {pkg}` (code {proc.returncode}):\n```\n{output}\n```",
                                parse_mode="Markdown")
        except asyncio.TimeoutError:
            await msg.edit_text(f"⏰ `apt {sub} {pkg}` timed out after 120s.", parse_mode="Markdown")
    else:
        await update.message.reply_text("Unknown subcommand. Use `search`, `install`, `remove`, or `update`.")
