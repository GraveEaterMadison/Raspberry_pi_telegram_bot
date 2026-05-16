"""handlers/gpio_handler.py — GPIO, PWM, Servo, I2C commands."""

import logging
import asyncio
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


def _get_gpio():
    """Try to import RPi.GPIO or gpiozero, fall back to simulation."""
    try:
        import RPi.GPIO as GPIO
        return GPIO, "RPi.GPIO"
    except ImportError:
        pass
    try:
        from gpiozero import LED, PWMOutputDevice
        return None, "gpiozero"
    except ImportError:
        return None, "simulation"


async def gpio_command(update: Update, context: CallbackContext) -> None:
    """Control a GPIO pin. Usage: /gpio <pin> <on|off>"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/gpio <pin_number> <on|off>`\nExample: `/gpio 18 on`",
            parse_mode="Markdown",
        )
        return

    try:
        pin = int(context.args[0])
        state = context.args[1].lower()
    except ValueError:
        await update.message.reply_text("❌ Pin must be a number.")
        return

    if state not in ("on", "off"):
        await update.message.reply_text("❌ State must be `on` or `off`.")
        return

    if not (2 <= pin <= 27):
        await update.message.reply_text("❌ Pin must be between 2 and 27 (BCM numbering).")
        return

    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH if state == "on" else GPIO.LOW)
        icon = "🟢" if state == "on" else "🔴"
        await update.message.reply_text(
            f"{icon} GPIO pin `{pin}` set to *{state.upper()}*",
            parse_mode="Markdown",
        )
    except ImportError:
        await update.message.reply_text(
            f"⚠️ *Simulation mode* (RPi.GPIO not installed)\n"
            f"Would set GPIO pin `{pin}` → `{state.upper()}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ GPIO error: `{e}`", parse_mode="Markdown")


async def pwm_command(update: Update, context: CallbackContext) -> None:
    """PWM control. Usage: /pwm <pin> <0-100>"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/pwm <pin> <duty_cycle 0-100>`\nExample: `/pwm 18 50`",
            parse_mode="Markdown",
        )
        return

    try:
        pin = int(context.args[0])
        duty = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid pin or duty cycle.")
        return

    if not 0 <= duty <= 100:
        await update.message.reply_text("❌ Duty cycle must be 0-100.")
        return

    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT)
        pwm = GPIO.PWM(pin, 1000)  # 1 kHz
        pwm.start(duty)
        bar = "█" * int(duty / 10) + "░" * (10 - int(duty / 10))
        await update.message.reply_text(
            f"〰️ *PWM* pin `{pin}` → `{duty:.1f}%`\n[`{bar}`]",
            parse_mode="Markdown",
        )
        # Keep PWM running for 5s then stop (stateless bot limitation)
        await asyncio.sleep(5)
        pwm.stop()
    except ImportError:
        await update.message.reply_text(
            f"⚠️ *Simulation* — PWM pin `{pin}` at `{duty:.1f}%`",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ PWM error: `{e}`", parse_mode="Markdown")


async def servo_command(update: Update, context: CallbackContext) -> None:
    """Control a servo motor. Usage: /servo <pin> <angle 0-180>"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/servo <pin> <angle 0-180>`\nExample: `/servo 18 90`",
            parse_mode="Markdown",
        )
        return

    try:
        pin   = int(context.args[0])
        angle = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid values.")
        return

    if not 0 <= angle <= 180:
        await update.message.reply_text("❌ Angle must be 0-180°.")
        return

    # Servo duty cycle: 2.5% = 0°, 12.5% = 180°
    duty = 2.5 + (angle / 180) * 10

    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin, GPIO.OUT)
        pwm = GPIO.PWM(pin, 50)  # 50 Hz for servo
        pwm.start(duty)
        await asyncio.sleep(0.5)
        pwm.stop()
        await update.message.reply_text(
            f"🦾 Servo on pin `{pin}` moved to `{angle:.0f}°`",
            parse_mode="Markdown",
        )
    except ImportError:
        await update.message.reply_text(
            f"⚠️ *Simulation* — Servo pin `{pin}` → `{angle:.0f}°`",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Servo error: `{e}`", parse_mode="Markdown")


async def i2c_command(update: Update, context: CallbackContext) -> None:
    """Scan I2C bus for connected devices."""
    msg = await update.message.reply_text("🔎 Scanning I2C bus...")
    try:
        proc = await asyncio.create_subprocess_exec(
            "i2cdetect", "-y", "1",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode() or stderr.decode()

        # Count detected devices
        devices = [cell for cell in output.split() if cell not in ("--", "UU")
                   and len(cell) == 2 and all(c in "0123456789abcdefABCDEF" for c in cell)]

        await msg.edit_text(
            f"🔎 *I2C Bus Scan*\n\n"
            f"Found `{len(devices)}` device(s){': ' + ', '.join('0x'+d for d in devices) if devices else ''}\n\n"
            f"```\n{output}\n```",
            parse_mode="Markdown",
        )
    except FileNotFoundError:
        await msg.edit_text(
            "❌ `i2cdetect` not found.\nInstall: `sudo apt install i2c-tools`\n"
            "Enable: `sudo raspi-config` → Interface Options → I2C",
            parse_mode="Markdown",
        )
    except Exception as e:
        await msg.edit_text(f"❌ I2C scan error: `{e}`", parse_mode="Markdown")
