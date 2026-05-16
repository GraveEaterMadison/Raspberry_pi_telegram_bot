"""handlers/camera.py — Pi Camera snapshot and motion detection."""
import asyncio
import io
import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext
from config import CAMERA_BACKEND, PIR_PIN

logger = logging.getLogger(__name__)
_motion_active = {}


async def snapshot_command(update: Update, context: CallbackContext) -> None:
    msg = await update.message.reply_text("📸 Capturing snapshot...")
    path = f"/tmp/snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    try:
        if CAMERA_BACKEND == "picamera2":
            proc = await asyncio.create_subprocess_exec(
                "libcamera-still", "-o", path, "--nopreview", "-t", "1000",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await asyncio.wait_for(proc.wait(), timeout=15)
        elif CAMERA_BACKEND == "opencv":
            import cv2
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                raise RuntimeError("OpenCV could not read from camera")
            cv2.imwrite(path, frame)
        else:
            # Fallback: raspistill
            proc = await asyncio.create_subprocess_exec(
                "raspistill", "-o", path, "-t", "500",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await asyncio.wait_for(proc.wait(), timeout=15)

        with open(path, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=f"📸 Snapshot @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            )
        os.unlink(path)
        await msg.delete()
    except asyncio.TimeoutError:
        await msg.edit_text("⏰ Camera timed out.")
    except Exception as e:
        await msg.edit_text(f"❌ Camera error: `{e}`\nMake sure the camera is enabled.", parse_mode="Markdown")


async def motion_command(update: Update, context: CallbackContext) -> None:
    uid = update.effective_user.id
    state = (context.args[0].lower() if context.args else "toggle")
    if state in ("on", "toggle") and not _motion_active.get(uid):
        _motion_active[uid] = True
        await update.message.reply_text("🚨 Motion detection *ON* — you'll be notified when motion is detected.", parse_mode="Markdown")
        asyncio.create_task(_motion_loop(update, context, uid))
    else:
        _motion_active[uid] = False
        await update.message.reply_text("✅ Motion detection *OFF*", parse_mode="Markdown")


async def _motion_loop(update: Update, context, uid: int):
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PIR_PIN, GPIO.IN)
        while _motion_active.get(uid):
            if GPIO.input(PIR_PIN):
                await context.bot.send_message(uid, "🚨 *MOTION DETECTED!*", parse_mode="Markdown")
                # Take snapshot
                path = f"/tmp/motion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "libcamera-still", "-o", path, "--nopreview", "-t", "500",
                        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                    )
                    await asyncio.wait_for(proc.wait(), timeout=10)
                    with open(path, "rb") as f:
                        await context.bot.send_photo(uid, photo=f, caption="📸 Motion capture")
                    os.unlink(path)
                except Exception:
                    pass
                await asyncio.sleep(10)  # cooldown
            await asyncio.sleep(0.5)
    except ImportError:
        await context.bot.send_message(uid, "⚠️ RPi.GPIO not available — motion detection requires real Pi hardware.")
    except Exception as e:
        logger.error("Motion loop error: %s", e)
