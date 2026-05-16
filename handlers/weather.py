"""handlers/weather.py — Weather via OpenWeatherMap."""
import aiohttp
import logging
from telegram import Update
from telegram.ext import CallbackContext
from config import OPENWEATHER_API_KEY

logger = logging.getLogger(__name__)
WEATHER_ICONS = {
    "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️", "Drizzle": "🌦️",
    "Thunderstorm": "⛈️", "Snow": "❄️", "Mist": "🌫️", "Fog": "🌫️",
}


async def weather_command(update: Update, context: CallbackContext) -> None:
    if not OPENWEATHER_API_KEY:
        await update.message.reply_text(
            "❌ Set `OPENWEATHER_API_KEY` in `.env` to use weather.\nGet a free key at openweathermap.org",
            parse_mode="Markdown",
        )
        return

    city = " ".join(context.args) if context.args else None

    if not city:
        # Try to get city from IP geolocation
        async with aiohttp.ClientSession() as session:
            try:
                r = await session.get("http://ip-api.com/json/", timeout=aiohttp.ClientTimeout(total=5))
                geo = await r.json()
                city = geo.get("city", "London")
            except Exception:
                city = "London"

    msg = await update.message.reply_text(f"🌍 Fetching weather for *{city}*...", parse_mode="Markdown")

    async with aiohttp.ClientSession() as session:
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            r = await session.get(url, params={
                "q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"
            }, timeout=aiohttp.ClientTimeout(total=10))
            if r.status == 404:
                await msg.edit_text(f"❌ City `{city}` not found.", parse_mode="Markdown")
                return
            data = await r.json()

            main = data["weather"][0]["main"]
            icon = WEATHER_ICONS.get(main, "🌡️")
            desc = data["weather"][0]["description"].capitalize()
            temp = data["main"]["temp"]
            feels = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind = data["wind"]["speed"]
            pressure = data["main"]["pressure"]
            visibility = data.get("visibility", 0) / 1000

            await msg.edit_text(
                f"{icon} *Weather in {data['name']}, {data['sys']['country']}*\n\n"
                f"🌡️ Temperature: `{temp:.1f}°C` (feels like `{feels:.1f}°C`)\n"
                f"💧 Humidity:    `{humidity}%`\n"
                f"🌬️ Wind:        `{wind:.1f} m/s`\n"
                f"📊 Pressure:    `{pressure} hPa`\n"
                f"👁️ Visibility:  `{visibility:.1f} km`\n"
                f"☁️ Condition:   `{desc}`",
                parse_mode="Markdown",
            )
        except Exception as e:
            await msg.edit_text(f"❌ Weather API error: `{e}`", parse_mode="Markdown")
