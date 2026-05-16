"""handlers/network.py — Network commands."""

import asyncio
import logging
import re
import socket
import subprocess
from typing import Optional

import psutil
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


async def ip_command(update: Update, context: CallbackContext) -> None:
    lines = ["🌐 *IP Addresses*\n"]
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                lines.append(f"• *{iface}:* `{addr.address}`")
            elif addr.family == socket.AF_INET6 and not addr.address.startswith("fe80"):
                lines.append(f"• *{iface} (IPv6):* `{addr.address}`")
    if not lines[1:]:
        lines.append("No IP addresses found.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def netinfo_command(update: Update, context: CallbackContext) -> None:
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    io = psutil.net_io_counters(pernic=True)
    lines = ["📡 *Network Interfaces*\n"]
    for iface, stat in stats.items():
        speed = f"{stat.speed} Mbps" if stat.speed else "unknown"
        up = "🟢 UP" if stat.isup else "🔴 DOWN"
        ip4 = next((a.address for a in addrs.get(iface, [])
                    if a.family == socket.AF_INET), "—")
        nic_io = io.get(iface)
        sent = f"{nic_io.bytes_sent >> 20:,} MB" if nic_io else "?"
        recv = f"{nic_io.bytes_recv >> 20:,} MB" if nic_io else "?"
        lines.append(
            f"*{iface}* {up} ({speed})\n"
            f"  IP: `{ip4}` | ↑ {sent} ↓ {recv}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def ping_command(update: Update, context: CallbackContext) -> None:
    args = context.args
    host = args[0] if args else "8.8.8.8"
    count = 4

    # Input validation
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        await update.message.reply_text("❌ Invalid host name.")
        return

    msg = await update.message.reply_text(f"🏓 Pinging `{host}`...", parse_mode="Markdown")
    proc = await asyncio.create_subprocess_exec(
        "ping", "-c", str(count), "-W", "3", host,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode() or stderr.decode()

    # Extract stats
    stats_line = next((l for l in output.splitlines() if "min/avg/max" in l), "")
    if stats_line:
        times = stats_line.split("=")[-1].strip().split("/")
        result = (
            f"🏓 *Ping* `{host}`\n\n"
            f"📊 min/avg/max: `{'/'.join(times[:3])} ms`\n\n"
            f"```\n{output[-800:]}\n```"
        )
    else:
        result = f"```\n{output[-1500:]}\n```"

    await msg.edit_text(result, parse_mode="Markdown")


async def wifi_command(update: Update, context: CallbackContext) -> None:
    msg = await update.message.reply_text("📶 Scanning WiFi networks...")
    try:
        proc = await asyncio.create_subprocess_exec(
            "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,BARS", "dev", "wifi", "list",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            # Fallback: try iwlist
            proc2 = await asyncio.create_subprocess_exec(
                "sudo", "iwlist", "wlan0", "scan",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc2.communicate()
            networks = _parse_iwlist(stdout.decode())
        else:
            networks = _parse_nmcli(stdout.decode())

        if not networks:
            await msg.edit_text("📶 No networks found (may need root).")
            return

        lines = ["📶 *Nearby WiFi Networks*\n"]
        for n in networks[:15]:
            lines.append(f"• `{n['ssid']:30s}` {n['signal']:4s} {n.get('security','')}")

        await msg.edit_text("\n".join(lines), parse_mode="Markdown")
    except FileNotFoundError:
        await msg.edit_text("❌ `nmcli`/`iwlist` not found. Install `network-manager`.")


def _parse_nmcli(output: str) -> list[dict]:
    nets = []
    for line in output.splitlines():
        parts = line.split(":")
        if len(parts) >= 4 and parts[0]:
            nets.append({"ssid": parts[0], "signal": parts[1] + "%",
                         "security": parts[2], "bars": parts[3]})
    return nets


def _parse_iwlist(output: str) -> list[dict]:
    nets = []
    current = {}
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Cell"):
            if current:
                nets.append(current)
            current = {}
        elif "ESSID:" in line:
            current["ssid"] = line.split('"')[1] if '"' in line else "Hidden"
        elif "Signal level=" in line:
            m = re.search(r"Signal level=(-?\d+)", line)
            current["signal"] = f"{m.group(1)} dBm" if m else "?"
    if current:
        nets.append(current)
    return nets


async def speedtest_command(update: Update, context: CallbackContext) -> None:
    msg = await update.message.reply_text("🚀 Running speed test... (this takes ~30s)")
    try:
        proc = await asyncio.create_subprocess_exec(
            "speedtest-cli", "--simple",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode().strip() or stderr.decode().strip()
        if not output:
            output = "No output — is speedtest-cli installed? (`pip install speedtest-cli`)"
        await msg.edit_text(f"🚀 *Speed Test Results*\n\n```\n{output}\n```",
                            parse_mode="Markdown")
    except asyncio.TimeoutError:
        await msg.edit_text("⏳ Speed test timed out after 60 seconds.")
    except FileNotFoundError:
        await msg.edit_text("❌ `speedtest-cli` not found. Run `/pkg install speedtest-cli`")


async def portscan_command(update: Update, context: CallbackContext) -> None:
    """Fast asyncio port scanner. Usage: /portscan host [start-end]"""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/portscan <host> [port_range]`\nExample: `/portscan 192.168.1.1 1-1024`",
            parse_mode="Markdown"
        )
        return

    host = context.args[0]
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        await update.message.reply_text("❌ Invalid host.")
        return

    port_range = context.args[1] if len(context.args) > 1 else "1-1024"
    try:
        start, end = map(int, port_range.split("-"))
        end = min(end, start + 500)  # cap at 500 ports
    except ValueError:
        await update.message.reply_text("❌ Invalid port range. Use format: `1-1024`")
        return

    msg = await update.message.reply_text(
        f"🔍 Scanning `{host}` ports {start}-{end}...", parse_mode="Markdown"
    )

    open_ports = []

    async def check_port(port: int):
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=0.5
            )
            writer.close()
            await writer.wait_closed()
            open_ports.append(port)
        except Exception:
            pass

    await asyncio.gather(*[check_port(p) for p in range(start, end + 1)])
    open_ports.sort()

    if open_ports:
        port_names = {22: "SSH", 80: "HTTP", 443: "HTTPS", 21: "FTP",
                      25: "SMTP", 3306: "MySQL", 5432: "Postgres", 6379: "Redis",
                      8080: "HTTP-Alt", 3000: "Dev", 8888: "Jupyter"}
        lines = ["🔍 *Open Ports*\n"]
        for p in open_ports:
            service = port_names.get(p, "unknown")
            lines.append(f"• Port `{p}` — {service}")
        await msg.edit_text("\n".join(lines), parse_mode="Markdown")
    else:
        await msg.edit_text(f"🔍 No open ports found on `{host}` in range {start}-{end}.",
                            parse_mode="Markdown")
