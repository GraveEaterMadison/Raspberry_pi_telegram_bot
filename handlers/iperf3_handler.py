"""handlers/iperf3_handler.py — iperf3 speed test handler.

Reads the most recent JSON result written by the background iperf3-speedtest
systemd service, or triggers a fresh run on demand.

Usage:
  /iperf3          → show latest saved result
  /iperf3 run      → trigger the systemd service to run a new test
  /iperf3 history  → show last N results with a trend line
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

# Default directory where the background CLI saves results
_RUNS_DIR = os.path.expanduser("~/.local/share/iperf3/runs/")
_SERVICE   = "iperf3-speedtest.service"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _latest_json(runs_dir: str = _RUNS_DIR) -> Optional[str]:
    files = glob.glob(os.path.join(runs_dir, "*.json"))
    return max(files, key=os.path.getmtime) if files else None


def _parse_result(data: dict) -> dict:
    """Extract the key metrics from an iperf3 JSON blob into a flat dict."""
    start    = data.get("start", {})
    end      = data.get("end", {})
    connected = start.get("connected", [])

    remote_host = connected[0].get("remote_host", "?") if connected else "?"

    # Timestamp → local tz
    ts_raw = start.get("timestamp", {}).get("time", "")
    try:
        dt = datetime.strptime(ts_raw, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        timestamp = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        timestamp = ts_raw or "?"

    sum_sent     = end.get("sum_sent",             {})
    sum_received = end.get("sum_received",          {})
    sum_reverse  = end.get("sum_sent_bidir_reverse", {})

    down_mbps = sum_received.get("bits_per_second", 0) / 1e6
    up_mbps   = (sum_reverse.get("bits_per_second", 0) or
                 sum_sent.get("bits_per_second", 0)) / 1e6

    retransmits = sum_sent.get("retransmits", 0)

    # RTT from first stream sender
    streams    = end.get("streams", [])
    sender     = streams[0].get("sender", {}) if streams else {}
    min_rtt    = sender.get("min_rtt",  0) / 1000   # µs → ms
    mean_rtt   = sender.get("mean_rtt", 0) / 1000
    max_rtt    = sender.get("max_rtt",  0) / 1000
    total_bytes = sender.get("bytes", 0)
    loss_pct   = (retransmits / (total_bytes / 1460)) * 100 if total_bytes > 0 else 0

    return dict(
        remote_host=remote_host, timestamp=timestamp,
        down_mbps=down_mbps, up_mbps=up_mbps,
        min_rtt=min_rtt, mean_rtt=mean_rtt, max_rtt=max_rtt,
        retransmits=retransmits, loss_pct=loss_pct,
    )


def _fmt(x: float) -> str:
    """Format a float, strip trailing zeros."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _speed_bar(mbps: float, max_mbps: float = 1000) -> str:
    filled = min(10, int(mbps / max_mbps * 10))
    return "█" * filled + "░" * (10 - filled)


def _render(m: dict) -> str:
    down_bar = _speed_bar(m["down_mbps"])
    up_bar   = _speed_bar(m["up_mbps"])
    lines = [
        f"📡 *iperf3 Result*",
        f"🌐 Server: `{m['remote_host']}` | 🕒 `{m['timestamp']}`",
        f"",
        f"📥 Down: `{_fmt(m['down_mbps'])} Mbps` [`{down_bar}`]",
        f"📤 Up:   `{_fmt(m['up_mbps'])} Mbps` [`{up_bar}`]",
    ]
    if m["mean_rtt"] > 0:
        lines.append(
            f"📶 RTT:  min `{_fmt(m['min_rtt'])}` / avg `{_fmt(m['mean_rtt'])}` / max `{_fmt(m['max_rtt'])}` ms"
        )
    if m["loss_pct"] > 0:
        lines.append(f"⚠️ Est. packet loss: `{m['loss_pct']:.2f}%`")
    if m["retransmits"] > 0:
        lines.append(f"🔄 Retransmits: `{m['retransmits']}`")
    return "\n".join(lines)


def _quality_verdict(m: dict) -> str:
    down = m["down_mbps"]
    rtt  = m["mean_rtt"]
    loss = m["loss_pct"]
    if loss > 2 or rtt > 100:
        return "🔴 Poor connection quality"
    if down < 10:
        return "🟠 Slow download speed"
    if down >= 100 and rtt < 30 and loss == 0:
        return "🟢 Excellent"
    if down >= 25:
        return "🟡 Good"
    return "🟠 Fair"


# ── Command ───────────────────────────────────────────────────────────────────

async def iperf3_command(update: Update, context: CallbackContext) -> None:
    """iperf3 speed test results and control.
    Usage: /iperf3 | /iperf3 run | /iperf3 history [n]
    """
    sub = context.args[0].lower() if context.args else "show"

    # ── /iperf3 run ──────────────────────────────────────────────────────────
    if sub == "run":
        msg = await update.message.reply_text("🚀 Triggering iperf3 speed test via systemd...")
        try:
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "--user", "restart", _SERVICE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode == 0:
                await msg.edit_text(
                    "✅ Speed test started in background.\n"
                    "Results will be saved automatically — check with `/iperf3` in ~30s.",
                    parse_mode="Markdown",
                )
            else:
                err = stderr.decode().strip()[:300]
                await msg.edit_text(
                    f"❌ Failed to start service:\n```\n{err}\n```\n\n"
                    f"Make sure `{_SERVICE}` is installed as a user service.",
                    parse_mode="Markdown",
                )
        except asyncio.TimeoutError:
            await msg.edit_text("⏰ Timed out starting the systemd service.")
        except FileNotFoundError:
            await msg.edit_text("❌ `systemctl` not found — are you on a systemd system?")
        return

    # ── /iperf3 history [n] ──────────────────────────────────────────────────
    if sub == "history":
        try:
            n = int(context.args[1]) if len(context.args) > 1 else 5
            n = max(1, min(n, 20))
        except ValueError:
            n = 5

        files = sorted(
            glob.glob(os.path.join(_RUNS_DIR, "*.json")),
            key=os.path.getmtime, reverse=True
        )[:n]

        if not files:
            await update.message.reply_text(
                "📭 No iperf3 results found.\n"
                f"Results dir: `{_RUNS_DIR}`\nRun `/iperf3 run` to start a test.",
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

        if not results:
            await update.message.reply_text("❌ Failed to parse any result files.")
            return

        # Trend arrow
        def _trend(vals):
            if len(vals) < 2:
                return ""
            return " ↗️" if vals[-1] > vals[0] else " ↘️" if vals[-1] < vals[0] else " →"

        downs = [r["down_mbps"] for r in results]
        ups   = [r["up_mbps"]   for r in results]
        lines = [f"📊 *iperf3 History* (last {len(results)} runs)\n"]
        for i, r in enumerate(results, 1):
            lines.append(
                f"*{i}.* `{r['timestamp']}` — "
                f"⬇{_fmt(r['down_mbps'])} / ⬆{_fmt(r['up_mbps'])} Mbps"
            )
        avg_down = sum(downs) / len(downs)
        avg_up   = sum(ups)   / len(ups)
        lines.append(
            f"\n📈 Avg: ⬇ `{_fmt(avg_down)} Mbps`{_trend(downs)}  "
            f"⬆ `{_fmt(avg_up)} Mbps`{_trend(ups)}"
        )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── /iperf3 (show latest) ────────────────────────────────────────────────
    latest = _latest_json()
    if not latest:
        await update.message.reply_text(
            "📭 No iperf3 results found.\n"
            f"Results directory: `{_RUNS_DIR}`\n\n"
            "Start a test with `/iperf3 run`, or configure the background service.",
            parse_mode="Markdown",
        )
        return

    try:
        with open(latest, encoding="utf-8") as f:
            data = json.load(f)
        m = _parse_result(data)
        verdict = _quality_verdict(m)
        text = _render(m) + f"\n\n{verdict}"
        await update.message.reply_text(text, parse_mode="Markdown")
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Latest result file is corrupted.")
    except Exception as e:
        logger.error("iperf3_command error: %s", e, exc_info=True)
        await update.message.reply_text(f"❌ Error reading result: `{e}`", parse_mode="Markdown")
