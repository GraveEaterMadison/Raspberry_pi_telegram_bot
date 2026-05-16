"""handlers/monitoring.py — Metric graphs, alerts, and metrics table."""

import io
import logging
import time
from datetime import datetime

from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

# Injected from main.py
_metrics = None


def set_metrics(m):
    global _metrics
    _metrics = m


async def graph_command(update: Update, context: CallbackContext) -> None:
    """Plot a metric history as an image. Usage: /graph <cpu|ram|temp>"""
    metric = (context.args[0].lower() if context.args else "cpu")
    if metric not in ("cpu", "ram", "temp"):
        await update.message.reply_text(
            "Usage: `/graph <cpu|ram|temp>`", parse_mode="Markdown"
        )
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        await update.message.reply_text(
            "❌ `matplotlib` not installed. Run: `pip install matplotlib`"
        )
        return

    history_map = {
        "cpu":  (_metrics.cpu_history  if _metrics else [], "CPU Usage (%)",    "#ff6b6b"),
        "ram":  (_metrics.ram_history  if _metrics else [], "RAM Usage (%)",    "#4dabf7"),
        "temp": (_metrics.temp_history if _metrics else [], "Temperature (°C)", "#f59f00"),
    }
    history, ylabel, color = history_map[metric]

    if not history or len(history) < 2:
        await update.message.reply_text(
            "⏳ Not enough data yet. Wait a few minutes for metrics to accumulate."
        )
        return

    timestamps = [datetime.fromtimestamp(t) for t, _ in history]
    values = [v for _, v in history]

    fig, ax = plt.subplots(figsize=(10, 4), facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")

    ax.plot(timestamps, values, color=color, linewidth=2, zorder=3)
    ax.fill_between(timestamps, values, alpha=0.3, color=color, zorder=2)

    ax.set_title(f"{metric.upper()} History", color="white", fontsize=14, fontweight="bold")
    ax.set_ylabel(ylabel, color="white")
    ax.tick_params(colors="white")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()

    for spine in ax.spines.values():
        spine.set_edgecolor("#444")
    ax.grid(True, color="#333", linestyle="--", alpha=0.5)

    avg_val = sum(values) / len(values)
    max_val = max(values)
    min_val = min(values)
    ax.axhline(avg_val, color="white", linestyle="--", alpha=0.5, linewidth=1)
    ax.text(timestamps[0], avg_val + 1, f"avg {avg_val:.1f}", color="white",
            fontsize=8, va="bottom")

    plt.figtext(0.99, 0.01, f"min={min_val:.1f} avg={avg_val:.1f} max={max_val:.1f}",
                ha="right", fontsize=8, color="gray")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    await update.message.reply_photo(
        photo=buf,
        caption=f"📊 *{metric.upper()} graph* — {len(values)} data points over ~{len(values)*10//60}min",
        parse_mode="Markdown",
    )


async def alert_command(update: Update, context: CallbackContext) -> None:
    """Manage resource alerts. Usage: /alert set cpu > 80 | /alert list | /alert clear"""
    args = context.args
    uid = update.effective_user.id

    if not args or args[0] == "list":
        if not _metrics:
            await update.message.reply_text("⏳ Metrics not yet initialised.")
            return
        alerts = _metrics.list_alerts(uid)
        if not alerts:
            await update.message.reply_text(
                "🔔 No alerts set. Use:\n`/alert set <cpu|ram|temp> <>/< threshold>`",
                parse_mode="Markdown"
            )
        else:
            lines = ["🔔 *Your Alerts*\n"]
            for a in alerts:
                lines.append(f"• `{a['metric']} {a['op']} {a['threshold']}`")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if args[0] == "clear":
        if _metrics:
            _metrics.clear_alerts(uid)
        await update.message.reply_text("✅ All alerts cleared.")
        return

    if args[0] == "set":
        if len(args) < 4:
            await update.message.reply_text(
                "Usage: `/alert set <cpu|ram|temp> <>/< threshold>`\n"
                "Example: `/alert set cpu > 85`",
                parse_mode="Markdown",
            )
            return
        metric = args[1].lower()
        op     = args[2]
        try:
            threshold = float(args[3])
        except ValueError:
            await update.message.reply_text("❌ Threshold must be a number.")
            return

        if metric not in ("cpu", "ram", "temp"):
            await update.message.reply_text("❌ Metric must be `cpu`, `ram`, or `temp`.")
            return
        if op not in (">", "<", ">=", "<="):
            await update.message.reply_text("❌ Operator must be `>`, `<`, `>=`, or `<=`.")
            return

        if _metrics:
            _metrics.add_alert(uid, metric, op, threshold)
        await update.message.reply_text(
            f"✅ Alert set: `{metric} {op} {threshold}` — you'll be notified when triggered.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        "Unknown subcommand. Use `set`, `list`, or `clear`.", parse_mode="Markdown"
    )


async def metrics_command(update: Update, context: CallbackContext) -> None:
    """Show recent metrics as a table."""
    if not _metrics:
        await update.message.reply_text("Metrics not available.")
        return

    cpu_last  = list(_metrics.cpu_history)[-10:]
    ram_last  = list(_metrics.ram_history)[-10:]
    temp_last = list(_metrics.temp_history)[-10:]

    if not cpu_last:
        await update.message.reply_text("⏳ No metrics yet. Wait a moment...")
        return

    lines = ["📈 *Recent Metrics* (last 10 readings)\n",
             "`  Time    CPU    RAM    Temp`",
             "`─────────────────────────────`"]

    # BUG FIX: original code assumed cpu_last, ram_last, temp_last are all the same
    # length and used the same index, but they can differ (e.g. temp returns None
    # on some ticks and is not appended). Use index-safe lookup.
    for i in range(len(cpu_last)):
        ts  = datetime.fromtimestamp(cpu_last[i][0]).strftime("%H:%M:%S")
        cpu = f"{cpu_last[i][1]:5.1f}%"
        ram = f"{ram_last[i][1]:5.1f}%" if i < len(ram_last)  else "  N/A "
        tmp = f"{temp_last[i][1]:5.1f}°" if i < len(temp_last) else "  N/A "
        lines.append(f"`{ts}  {cpu}  {ram}  {tmp}`")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
