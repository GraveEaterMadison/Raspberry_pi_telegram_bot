import time
import logging
from collections import defaultdict
from typing import Callable, Awaitable
from functools import wraps

from telegram import Update
from telegram.ext import CallbackContext

from config import AUTHORIZED_USERS, RATE_LIMIT_PER_MINUTE

logger = logging.getLogger(__name__)

# ── Rate limiter ──────────────────────────────────────────────────────────────
_rate_buckets: dict[int, list[float]] = defaultdict(list)


def _is_rate_limited(user_id: int) -> bool:
    now = time.monotonic()
    window = 60.0
    # BUG FIX: was reading stale `bucket` variable then overwriting it;
    # now we work on the already-filtered list consistently.
    _rate_buckets[user_id] = [t for t in _rate_buckets[user_id] if now - t < window]
    if len(_rate_buckets[user_id]) >= RATE_LIMIT_PER_MINUTE:
        return True
    _rate_buckets[user_id].append(now)
    return False


# ── Authorization wrapper ─────────────────────────────────────────────────────
async def require_auth(
    update: Update,
    context: CallbackContext,
    *,
    handler: Callable[[Update, CallbackContext], Awaitable[None]],
    audit=None,
) -> None:
    """
    Middleware that checks if the user is authorized before calling the handler.
    Also enforces rate limiting and writes to the audit log.
    """
    user = update.effective_user
    if user is None:
        return

    uid = user.id
    uname = user.username or user.full_name

    # Authorization check
    if AUTHORIZED_USERS and uid not in AUTHORIZED_USERS:
        logger.warning("Unauthorized access attempt by %s (id=%d)", uname, uid)
        await update.effective_message.reply_text(
            "🚫 Access denied. You are not authorized to use this bot."
        )
        return

    # Rate limiting
    if _is_rate_limited(uid):
        await update.effective_message.reply_text(
            f"⏳ Slow down! You're sending too many commands. "
            f"Limit: {RATE_LIMIT_PER_MINUTE} commands/minute."
        )
        return

    # Audit log
    if audit:
        cmd = update.effective_message.text or "<no text>"
        audit.log(uid, uname, cmd)

    # Call the real handler
    try:
        await handler(update, context)
    except Exception as e:
        logger.error("Handler %s raised: %s", handler.__name__, e, exc_info=True)
        await update.effective_message.reply_text(
            f"⚠️ Command failed:\n`{type(e).__name__}: {e}`",
            parse_mode="Markdown",
        )
