"""handlers/notes.py — SQLite-backed notes."""
import sqlite3
import logging
from telegram import Update
from telegram.ext import CallbackContext
from config import DB_PATH

logger = logging.getLogger(__name__)


def _init_notes():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ts TEXT, text TEXT)""")


async def note_command(update: Update, context: CallbackContext) -> None:
    _init_notes()
    uid = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage:\n`/note add <text>` — Add note\n`/note list` — List notes\n`/note del <id>` — Delete",
            parse_mode="Markdown",
        )
        return

    sub = args[0].lower()
    if sub == "add":
        text = " ".join(args[1:])
        if not text:
            await update.message.reply_text("❌ Note text cannot be empty.")
            return
        from datetime import datetime
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO notes(user_id,ts,text) VALUES(?,?,?)", (uid, ts, text))
        await update.message.reply_text("✅ Note saved!")

    elif sub == "list":
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id,ts,text FROM notes WHERE user_id=? ORDER BY id DESC LIMIT 20", (uid,)
            ).fetchall()
        if not rows:
            await update.message.reply_text("📝 No notes yet. Use `/note add <text>`.", parse_mode="Markdown")
            return
        lines = ["📝 *Your Notes*\n"]
        for row_id, ts, text in rows:
            lines.append(f"*#{row_id}* `{ts}`\n  {text}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    elif sub == "del":
        try:
            note_id = int(args[1])
        except (IndexError, ValueError):
            await update.message.reply_text("Usage: `/note del <id>`", parse_mode="Markdown")
            return
        with sqlite3.connect(DB_PATH) as conn:
            count = conn.execute(
                "DELETE FROM notes WHERE id=? AND user_id=?", (note_id, uid)
            ).rowcount
        if count:
            await update.message.reply_text(f"✅ Note #{note_id} deleted.")
        else:
            await update.message.reply_text(f"❌ Note #{note_id} not found.")
    else:
        await update.message.reply_text("Unknown subcommand. Use `add`, `list`, or `del`.", parse_mode="Markdown")
