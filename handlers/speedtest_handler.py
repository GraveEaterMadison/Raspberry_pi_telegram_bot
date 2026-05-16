"""handlers/speedtest_handler.py — Cloudflare speed test handler.

Reads the most recent JSON result written by the cloudflare-speed-cli
background systemd service, or triggers a fresh run on demand.

Usage:
  /speedtest           → show latest saved result
  /speedtest run       → trigger the systemd service
  /speedtest history   → show last N results with trend
"""

import asyncio
import glob
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

_RUNS_DIR = os.path.expanduser("~/.local/share/cloudflare-speed-cli/runs/")
_SERVICE  = "cloudflare-speedtest.service"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _latest_json(runs_dir: str = _RUNS_DIR) -> Optional[str]:
    files = glob.glob(os.path.join(runs_dir, "run-*.json"))
    return max(files, key=os.path.getmtime) if files else None


def _parse_result(data: dict) -> dict:
    country  = data.get("meta", {}).get("country", "?")
    server   = data.get("server", "?")

    utc_str = data.get("timestamp_utc", "")
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        timestamp = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        timestamp = utc_str or "?"

    idle  = data.get("idle_latency", {})
    ping  = int(idle.get("median_ms", 0))
    jitter = round(idle.get("jitter_ms", 0), 1)
    loss  = round(idle.get("loss", 0) * 100, 1)
    down_mbps = data.get("download", {}).get("mbps", 0)
    up_mbps   = data.get("upload",   {}).get("mbps", 0)

    return dict(
        country=country, server=server, timestamp=timestamp,
        ping=ping, jitter=jitter, loss=loss,
        down_mbps=down_mbps, up_mbps=up_mbps,
    )


def _fmt(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _speed_bar(mbps: float, max_mbps: float = 1000) -> str:
    filled = min(10, int(mbps / max_mbps * 10))
    return "█" * filled + "░" * (10 - filled)


def _render(m: dict) -> str:
    down_bar = _speed_bar(m["down_mbps"])
    up_bar   = _speed_bar(m["up_mbps"])
    lines = [
        f"⚡ *Cloudflare Speed Test*",
        f"🌐 `{m['country']}` → `{m['server']}` | 🕒 `{m['timestamp']}`",
        f"",
        f"📥 Down: `{_fmt(m['down_mbps'])} Mbps` [`{down_bar}`]",
        f"📤 Up:   `{_fmt(m['up_mbps'])} Mbps` [`{up_bar}`]",
        f"📶 Ping: `{m['ping']} ms` | Jitter: `{m['jitter']} ms`",
    ]
    if m["loss"] > 0:
        lines.append(f"⚠️ Packet loss: `{m['loss']}%`")
    return "\n".join(lines)


def _quality_verdict(m: dict) -> str:
    if m["loss"] > 2 or m["ping"] > 150:
        return "🔴 Poor connection quality"
    if m["down_mbps"] < 5:
        return "🔴 Very slow download"
    if m["down_mbps"] >= 100 and m["ping"] < 30 and m["loss"] == 0:
        return "🟢 Excellent"
    if m["down_mbps"] >= 25:
        return "🟡 Good"
    return "🟠 Fair"


# ── Command ───────────────────────────────────────────────────────────────────

async def cloudflare_speedtest_command(update: Update, context: CallbackContext) -> None:
    """Cloudflare speed test results.
    Usage: /cfspeed | /cfspeed run | /cfspeed history [n]
    """
    sub = context.args[0].lower() if context.args else "show"

    # ── run ──────────────────────────────────────────────────────────────────
    if sub == "run":
        msg = await update.message.reply_text("🚀 Triggering Cloudflare speed test via systemd...")
        try:
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "--user", "restart", _SERVICE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode == 0:
                await msg.edit_text(
                    "✅ Speed test started in background.\n"
                    "Check results with `/cfspeed` in ~30s.",
                    parse_mode="Markdown",
                )
            else:
                err = stderr.decode().strip()[:300]
                await msg.edit_text(
                    f"❌ Failed to start service:\n```\n{err}\n```",
                    parse_mode="Markdown",
                )
        except asyncio.TimeoutError:
            await msg.edit_text("⏰ Timed out starting the systemd service.")
        except FileNotFoundError:
            await msg.edit_text("❌ `systemctl` not found.")
        return

    # ── history ───────────────────────────────────────────────────────────────
    if sub == "history":
        try:
            n = int(context.args[1]) if len(context.args) > 1 else 5
            n = max(1, min(n, 20))
        except ValueError:
            n = 5

        files = sorted(
            glob.glob(os.path.join(_RUNS_DIR, "run-*.json")),
            key=os.path.getmtime, reverse=True
        )[:n]

        if not files:
            await update.message.reply_text(
                f"📭 No Cloudflare speed results found.\n`{_RUNS_DIR}`",
                parse_mode="Markdown",
            )
            return

        results = []
        for f in files:
            try:
                with open(f, encoding="utf-8") as fh:
                    results.append(_parse_result(json.load(fh)))
            except Exception:
                continue

        def _trend(vals):
            if len(vals) < 2:
                return ""
            return " ↗️" if vals[-1] > vals[0] else " ↘️" if vals[-1] < vals[0] else " →"

        downs = [r["down_mbps"] for r in results]
        ups   = [r["up_mbps"]   for r in results]
        lines = [f"📊 *Cloudflare Speed History* (last {len(results)} runs)\n"]
        for i, r in enumerate(results, 1):
            lines.append(
                f"*{i}.* `{r['timestamp']}` — "
                f"⬇{_fmt(r['down_mbps'])} / ⬆{_fmt(r['up_mbps'])} Mbps  📶{r['ping']}ms"
            )
        avg_down = sum(downs) / len(downs)
        avg_up   = sum(ups)   / len(ups)
        lines.append(
            f"\n📈 Avg: ⬇ `{_fmt(avg_down)} Mbps`{_trend(downs)}  "
            f"⬆ `{_fmt(avg_up)} Mbps`{_trend(ups)}"
        )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── show latest ───────────────────────────────────────────────────────────
    latest = _latest_json()
    if not latest:
        await update.message.reply_text(
            "📭 No Cloudflare speed results found.\n"
            f"Results dir: `{_RUNS_DIR}`\n\n"
            "Run `/cfspeed run` to start a test.",
            parse_mode="Markdown",
        )
        return

    try:
        with open(latest, encoding="utf-8") as f:
            data = json.load(f)
        m       = _parse_result(data)
        verdict = _quality_verdict(m)
        text    = _render(m) + f"\n\n{verdict}"
        await update.message.reply_text(text, parse_mode="Markdown")
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Latest result file is corrupted.")
    except Exception as e:
        logger.error("cfspeed_command error: %s", e, exc_info=True)
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode="Markdown")
