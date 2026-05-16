"""handlers/sensors.py — Multi-sensor hub."""
import logging
from telegram import Update
from telegram.ext import CallbackContext
from config import DHT_SENSOR_TYPE, DHT_PIN, BMP280_ADDRESS

logger = logging.getLogger(__name__)


async def sensors_command(update: Update, context: CallbackContext) -> None:
    lines = ["🌡️ *Sensor Readings*\n"]

    # DHT22/DHT11
    try:
        import adafruit_dht
        import board
        pin = getattr(board, f"D{DHT_PIN}")
        sensor = adafruit_dht.DHT22(pin) if DHT_SENSOR_TYPE == "DHT22" else adafruit_dht.DHT11(pin)
        lines.append(f"🌡️ *{DHT_SENSOR_TYPE}* (pin {DHT_PIN})")
        lines.append(f"  Temperature: `{sensor.temperature:.1f}°C`")
        lines.append(f"  Humidity:    `{sensor.humidity:.1f}%`\n")
    except ImportError:
        lines.append("⚠️ DHT: `adafruit-circuitpython-dht` not installed")
    except Exception as e:
        lines.append(f"❌ DHT error: `{e}`")

    # BMP280
    try:
        import smbus2
        from bmp280 import BMP280
        bus = smbus2.SMBus(1)
        bmp = BMP280(i2c_dev=bus, i2c_addr=BMP280_ADDRESS)
        lines.append(f"\n🔵 *BMP280* (0x{BMP280_ADDRESS:02x})")
        lines.append(f"  Temperature: `{bmp.get_temperature():.2f}°C`")
        lines.append(f"  Pressure:    `{bmp.get_pressure():.2f} hPa`")
        altitude = 44330 * (1 - (bmp.get_pressure() / 1013.25) ** 0.1903)
        lines.append(f"  Altitude:    ~`{altitude:.1f} m`\n")
    except ImportError:
        lines.append("\n⚠️ BMP280: `bmp280` library not installed")
    except Exception as e:
        lines.append(f"\n❌ BMP280 error: `{e}`")

    # CPU temp always available
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            t = int(f.read()) / 1000
        lines.append(f"\n🖥️ *CPU Thermal*: `{t:.1f}°C`")
    except Exception:
        pass

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
