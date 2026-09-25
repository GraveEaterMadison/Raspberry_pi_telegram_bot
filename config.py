import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file

# ── Required ──────────────────────────────────────────────────────────────────
API_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]

# Comma-separated list of authorized Telegram user IDs, e.g. "123456789,987654321"
_raw_users = os.getenv("AUTHORIZED_USERS", "")
AUTHORIZED_USERS: list[int] = [
    int(uid.strip()) for uid in _raw_users.split(",") if uid.strip().isdigit()
]

# ── Optional features ─────────────────────────────────────────────────────────
# AI backend (openai or anthropic) — used as a plain Q&A fallback for /ai
# when ANTHROPIC_API_KEY isn't set. The intelligent chat/tool routing always
# uses Anthropic, since only that path knows how to drive the bot's tools.
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "anthropic")  # or "openai"
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Cheapest current Claude model — used for both /ai and the smart chat router.
AI_MODEL: str = os.getenv("AI_MODEL", "claude-haiku-4-5-20251001")

# Cap on Claude's reply length (tokens) — keeps every call cheap and fast.
AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "400"))

# Whether every plain chat message (no leading /) is sent to the AI, which
# then decides to either chat back or call one of the bot's commands.
AI_SMART_CHAT: bool = os.getenv("AI_SMART_CHAT", "true").strip().lower() in ("1", "true", "yes")

# Commands to hide from the AI entirely (comma-separated command names,
# without the leading /). They remain usable as normal slash commands.
AI_EXCLUDED_COMMANDS: list[str] = [
    c.strip().lstrip("/") for c in os.getenv("AI_EXCLUDED_COMMANDS", "").split(",") if c.strip()
]

# ── /integrate — turn a GitHub repo into a new AI skill ────────────────────────
# Directory cloned repos live in (persists across restarts).
VENDOR_DIR: str = os.getenv("VENDOR_DIR", "data/vendor")

# Larger token budget for the one-off code-generation call than normal chat.
AI_INTEGRATION_MAX_TOKENS: int = int(os.getenv("AI_INTEGRATION_MAX_TOKENS", "2000"))

# Timeouts (seconds) for cloning a repo and for installing its dependencies.
INTEGRATION_CLONE_TIMEOUT: int = int(os.getenv("INTEGRATION_CLONE_TIMEOUT", "90"))
INTEGRATION_INSTALL_TIMEOUT: int = int(os.getenv("INTEGRATION_INSTALL_TIMEOUT", "180"))

# OpenWeatherMap API key for /weather command
OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

# Pi camera (picamera2 or opencv or dummy)
CAMERA_BACKEND: str = os.getenv("CAMERA_BACKEND", "picamera2")

# GPIO mode: BCM or BOARD (default BCM)
GPIO_MODE: str = os.getenv("GPIO_MODE", "BCM")

# DHT sensor type: DHT11 or DHT22
DHT_SENSOR_TYPE: str = os.getenv("DHT_SENSOR_TYPE", "DHT22")
DHT_PIN: int = int(os.getenv("DHT_PIN", "4"))

# BMP280 I2C address (default 0x76)
BMP280_ADDRESS: int = int(os.getenv("BMP280_ADDRESS", "0x76"), 16)

# Motion sensor (PIR) GPIO pin
PIR_PIN: int = int(os.getenv("PIR_PIN", "17"))

# Backup paths — comma-separated
BACKUP_PATHS: list[str] = [
    p.strip() for p in os.getenv("BACKUP_PATHS", "/home/pi,/etc").split(",")
]

# Max exec output length (chars)
MAX_EXEC_OUTPUT: int = int(os.getenv("MAX_EXEC_OUTPUT", "4000"))

# Rate limiting: max commands per user per minute
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

# Metrics history size (number of data points to keep in memory)
METRICS_HISTORY_SIZE: int = int(os.getenv("METRICS_HISTORY_SIZE", "60"))

# Metrics collection interval (seconds)
METRICS_INTERVAL: int = int(os.getenv("METRICS_INTERVAL", "10"))

# Logging level
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# SQLite database for audit log & notes
DB_PATH: str = os.getenv("DB_PATH", "data/bot.db")

# Allowed shell commands (whitelist mode, empty = allow all for authorized users)
EXEC_WHITELIST: list[str] = [
    c.strip() for c in os.getenv("EXEC_WHITELIST", "").split(",") if c.strip()
]

# Blocked shell commands (always blocked even for authorized users)
EXEC_BLACKLIST: list[str] = [
    c.strip() for c in os.getenv(
        "EXEC_BLACKLIST", "rm -rf /,mkfs,dd if=/dev/zero"
    ).split(",") if c.strip()
]

# Validate
if not API_TOKEN or API_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    raise ValueError(
        "❌ TELEGRAM_BOT_TOKEN is not set! Copy .env.example to .env and fill it in."
    )
 
