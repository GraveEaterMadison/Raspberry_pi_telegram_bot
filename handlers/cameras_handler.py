

import asyncio
import logging
import re

from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


async def _run(cmd: list, timeout: int = 8) -> tuple[int, str, str]:
    """Run a subprocess, return (returncode, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")
    except asyncio.TimeoutError:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -2, "", "not_found"


def _parse_rpicam(output: str) -> list[dict]:
    """Parse rpicam-hello --list-cameras output into a list of camera dicts."""
    cameras = []
    current: dict = {}
    for line in output.splitlines():
        # New camera entry: "0 : imx708 [4608x2592 10-bit RGGB]"
        m = re.match(r"^\s*(\d+)\s*:\s*(.+)", line)
        if m:
            if current:
                cameras.append(current)
            current = {"index": int(m.group(1)), "raw": m.group(2).strip()}
            # Parse model + resolution if present
            inner = re.match(r"(.+?)\s*\[(.+?)\]", current["raw"])
            if inner:
                current["model"]      = inner.group(1).strip()
                current["resolution"] = inner.group(2).strip()
            else:
                current["model"]      = current["raw"]
                current["resolution"] = "?"
        elif current and line.strip():
            # Additional properties indented under a camera entry
            current.setdefault("props", []).append(line.strip())
    if current:
        cameras.append(current)
    return cameras


def _parse_v4l2(output: str) -> list[dict]:
    """Parse v4l2-ctl --list-devices output."""
    cameras = []
    current_name = ""
    for line in output.splitlines():
        if line and not line.startswith("\t"):
            current_name = line.strip().rstrip(":")
        elif line.startswith("\t") and current_name:
            dev = line.strip()
            cameras.append({"model": current_name, "device": dev, "index": len(cameras)})
    return cameras


async def cameras_command(update: Update, context: CallbackContext) -> None:
    """List all detected cameras — Pi Camera Modules and USB cameras."""
    msg = await update.message.reply_text("🎥 Scanning for cameras...")

    lines = ["🎥 *Connected Cameras*\n"]
    found_any = False

    # ── 1. rpicam / libcamera (Pi Camera Modules) ────────────────────────────
    rc, stdout, stderr = await _run(["rpicam-hello", "--list-cameras"])
    if rc == -2:
        # rpicam-hello not found — try libcamera-hello (older alias)
        rc, stdout, stderr = await _run(["libcamera-hello", "--list-cameras"])

    if rc == -1:
        lines.append("⚠️ `rpicam-hello` timed out.")
    elif rc == -2:
        lines.append("ℹ️ `rpicam-hello` / `libcamera-hello` not installed.")
    else:
        # The output goes to stderr on some versions
        raw = stdout or stderr
        cameras = _parse_rpicam(raw)
        if cameras:
            found_any = True
            lines.append("*📷 Pi Camera Modules (libcamera)*")
            for cam in cameras:
                lines.append(
                    f"  `[{cam['index']}]` *{cam.get('model', '?')}*"
                    + (f" — `{cam['resolution']}`" if cam.get("resolution") and cam["resolution"] != "?" else "")
                )
                for prop in cam.get("props", []):
                    lines.append(f"       `{prop}`")
            lines.append("")
        elif "No cameras available" in raw or "no cameras" in raw.lower():
            lines.append("ℹ️ No Pi camera modules detected via libcamera.")
        else:
            lines.append(f"⚠️ Unexpected rpicam output:\n```\n{raw[:400]}\n```")

    # ── 2. v4l2 (USB cameras) ─────────────────────────────────────────────────
    rc2, stdout2, stderr2 = await _run(["v4l2-ctl", "--list-devices"])
    if rc2 == -2:
        lines.append("ℹ️ `v4l2-ctl` not installed (`sudo apt install v4l-utils`).")
    elif rc2 == -1:
        lines.append("⚠️ `v4l2-ctl` timed out.")
    elif rc2 == 0 and stdout2.strip():
        usb_cams = _parse_v4l2(stdout2)
        # Filter out pure Pi camera entries already shown
        usb_cams = [c for c in usb_cams if "mmal" not in c["model"].lower()
                    and "unicam" not in c["model"].lower()]
        if usb_cams:
            found_any = True
            lines.append("*🎥 USB / V4L2 Cameras*")
            for cam in usb_cams:
                lines.append(f"  `[{cam['index']}]` *{cam['model']}* — `{cam['device']}`")

    if not found_any:
        lines.append("\n❌ No cameras detected.\n"
                     "Check cable, enable camera via `raspi-config`, or install `v4l-utils`.")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown")
