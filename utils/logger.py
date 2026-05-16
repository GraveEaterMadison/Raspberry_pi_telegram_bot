"""utils/logger.py — SQLite-backed audit log."""

import sqlite3
import logging
from datetime import datetime, timezone
from config import DB_PATH

logger = logging.getLogger(__name__)


class AuditLogger:
    def init(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts        TEXT    NOT NULL,
                    user_id   INTEGER NOT NULL,
                    username  TEXT,
                    command   TEXT    NOT NULL
                )
            """)
        logger.info("Audit log initialized at %s", DB_PATH)

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    def log(self, user_id: int, username: str, command: str):
        ts = datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds")
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO audit_log(ts,user_id,username,command) VALUES(?,?,?,?)",
                    (ts, user_id, username, command),
                )
        except Exception as e:
            logger.error("Audit log write failed: %s", e)

    def recent(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT ts,username,command FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [{"ts": r[0], "username": r[1], "command": r[2]} for r in rows]
