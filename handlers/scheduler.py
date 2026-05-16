"""handlers/scheduler.py — Task scheduler and cron manager."""
import asyncio
import logging
import re
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from config import DB_PATH

logger = logging.getLogger(__name__)


def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, chat_id INTEGER,
            run_at TEXT, command TEXT, done INTEGER DEFAULT 0)""")


async def schedule_command(update: Update, context: CallbackContext) -> None:
    """/schedule HH:MM /command arg1 arg2"""
    _init_db()
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/schedule HH:MM <command>`\nExample: `/schedule 23:00 /reboot`",
            parse_mode="Markdown",
        )
        return

    time_str = context.args[0]
    command  = " ".join(context.args[1:])

    if not re.match(r'^\d{2}:\d{2}$', time_str):
        await update.message.reply_text("❌ Time must be in HH:MM format (24h).")
        return

    uid = update.effective_user.id
    cid = update.effective_chat.id

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO scheduled_tasks(user_id,chat_id,run_at,command) VALUES(?,?,?,?)",
            (uid, cid, time_str, command),
        )

    await update.message.reply_text(
        f"✅ Scheduled `{command}` to run daily at `{time_str}`.",
        parse_mode="Markdown",
    )


async def cron_command(update: Update, context: CallbackContext) -> None:
    _init_db()
    args = context.args
    uid  = update.effective_user.id
    sub  = args[0].lower() if args else "list"

    if sub == "list":
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id,run_at,command FROM scheduled_tasks WHERE user_id=? AND done=0",
                (uid,)
            ).fetchall()
        if not rows:
            await update.message.reply_text("🗓️ No scheduled tasks. Use `/schedule HH:MM /command`.",
                                             parse_mode="Markdown")
            return
        lines = ["🗓️ *Scheduled Tasks*\n"]
        for row_id, run_at, cmd in rows:
            lines.append(f"*#{row_id}* @ `{run_at}` — `{cmd}`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    elif sub == "del":
        try:
            task_id = int(args[1])
        except (IndexError, ValueError):
            await update.message.reply_text("Usage: `/cron del <id>`", parse_mode="Markdown")
            return
        with sqlite3.connect(DB_PATH) as conn:
            count = conn.execute(
                "DELETE FROM scheduled_tasks WHERE id=? AND user_id=?", (task_id, uid)
            ).rowcount
        if count:
            await update.message.reply_text(f"✅ Task #{task_id} deleted.")
        else:
            await update.message.reply_text(f"❌ Task #{task_id} not found.")

    else:
        await update.message.reply_text("Unknown subcommand. Use `list` or `del`.", parse_mode="Markdown")


async def scheduler_loop(bot):
    """Background task: run scheduled commands at their HH:MM times."""
    _init_db()
    while True:
        now = datetime.now().strftime("%H:%M")
        try:
            with sqlite3.connect(DB_PATH) as conn:
                tasks = conn.execute(
                    "SELECT id,user_id,chat_id,command FROM scheduled_tasks WHERE run_at=? AND done=0",
                    (now,)
                ).fetchall()

            for task_id, uid, cid, command in tasks:
                try:
                    await bot.send_message(
                        cid,
                        f"⏰ *Scheduled task running:*\n`{command}`",
                        parse_mode="Markdown",
                    )
                    # Execute the command as a shell process
                    proc = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                    )
                    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                    output = stdout.decode(errors="replace").strip()[-2000:]
                    await bot.send_message(
                        cid,
                        f"✅ Done (exit `{proc.returncode}`):\n```\n{output or '(no output)'}\n```",
                        parse_mode="Markdown",
                    )
                    logger.info("Scheduler ran task #%d: %s (exit %d)", task_id, command, proc.returncode)
                except asyncio.TimeoutError:
                    await bot.send_message(cid, f"⏰ Scheduled task timed out:\n`{command}`",
                                           parse_mode="Markdown")
                except Exception as e:
                    logger.error("Scheduled task #%d failed: %s", task_id, e)
                    await bot.send_message(cid, f"❌ Scheduled task failed:\n`{e}`",
                                           parse_mode="Markdown")

        except Exception as e:
            logger.error("Scheduler loop error: %s", e)

        await asyncio.sleep(60)
