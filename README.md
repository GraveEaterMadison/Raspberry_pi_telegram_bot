# Raspberry Pi Telegram Bot

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Model%20B-orange)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

A versatile Telegram bot that runs on a Raspberry Pi, allowing you to control your Pi and interact with it remotely via Telegram. Monitor system health, control GPIO pins, manage files, run shell commands, take camera snapshots, and much more — all from Telegram.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running as a Service](#running-as-a-service)
- [Commands](#commands)
- [File Structure](#file-structure)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **System Monitoring** — CPU, RAM, disk, temperature, uptime, and an overall health score
- **Interactive Dashboard** — Inline keyboard control panel with live stats
- **Remote Shell** — Execute shell commands with blacklist/whitelist safety filters
- **File Manager** — List, read, download, and upload files
- **GPIO Control** — Digital on/off, PWM duty cycle, servo motor angles, I2C bus scanner
- **Camera** — Take snapshots and run motion detection with auto-capture
- **Network Tools** — IP info, WiFi scan, ping, port scanner, speed test
- **Process Manager** — List top processes and kill by PID
- **Metrics & Alerts** — Background metrics collection with plotted graphs and threshold alerts
- **AI Assistant** — Ask questions via Anthropic Claude or OpenAI GPT
- **Task Scheduler** — Schedule commands to run daily at a set time; manage cron jobs
- **Package Manager** — Search, install, and remove APT packages
- **Backup** — Create and send `.tar.gz` backups of Pi directories to Telegram
- **Weather** — Current weather via OpenWeatherMap
- **Sensor Hub** — Read DHT11/DHT22, BMP280, and PIR sensors
- **Notes** — Per-user SQLite-backed notes
- **Authorization & Rate Limiting** — Only whitelisted user IDs can use the bot
- **Audit Log** — Every command logged to SQLite with timestamp and user info

---

## Requirements

- Raspberry Pi running Raspberry Pi OS (Debian-based)
- Python 3.11+
- A Telegram account and bot token from [@BotFather](https://t.me/BotFather)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/GraveEaterMadison/Raspberry_pi_telegram_bot.git
cd Raspberry_pi_telegram_bot
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

For optional hardware support, uncomment the relevant lines in `requirements.txt` first, then re-run the above. Or install manually:

```bash
# GPIO
pip install RPi.GPIO

# Camera (Pi 4 and newer)
pip install picamera2

# DHT11 / DHT22 sensors
pip install adafruit-circuitpython-dht adafruit-blinka

# BMP280 pressure/temperature sensor
pip install bmp280 smbus2

# I2C tools (via apt, not pip)
sudo apt install i2c-tools python3-smbus

# Internet speed test
pip install speedtest-cli
```

### 4. Create your bot on Telegram

- Message [@BotFather](https://t.me/BotFather) and run `/newbot`
- Follow the prompts and copy the API token it gives you

### 5. Set up your environment file

```bash
cp .env.example .env
nano .env
```

At minimum set these two values:

```env
TELEGRAM_BOT_TOKEN=your_token_here
AUTHORIZED_USERS=123456789
```

To find your Telegram user ID, message [@userinfobot](https://t.me/userinfobot).

### 6. Run the bot

```bash
python main.py
```

---

## Configuration

All configuration is done through the `.env` file. Copy `.env.example` to `.env` and fill in your values.

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Token from @BotFather |
| `AUTHORIZED_USERS` | ✅ | — | Comma-separated Telegram user IDs, e.g. `123456789,987654321` |
| `AI_PROVIDER` | No | `anthropic` | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` | No | — | For `/ai` command (get at console.anthropic.com) |
| `OPENAI_API_KEY` | No | — | For `/ai` command via OpenAI |
| `OPENWEATHER_API_KEY` | No | — | For `/weather` (free key at openweathermap.org) |
| `CAMERA_BACKEND` | No | `picamera2` | `picamera2`, `opencv`, or `dummy` |
| `GPIO_MODE` | No | `BCM` | `BCM` or `BOARD` |
| `DHT_SENSOR_TYPE` | No | `DHT22` | `DHT11` or `DHT22` |
| `DHT_PIN` | No | `4` | GPIO pin number for DHT sensor |
| `BMP280_ADDRESS` | No | `0x76` | I2C address of BMP280 sensor |
| `PIR_PIN` | No | `17` | GPIO pin number for PIR motion sensor |
| `BACKUP_PATHS` | No | `/home/pi,/etc` | Comma-separated paths to back up |
| `MAX_EXEC_OUTPUT` | No | `4000` | Max characters of shell command output |
| `RATE_LIMIT_PER_MINUTE` | No | `20` | Max commands per user per minute |
| `METRICS_HISTORY_SIZE` | No | `60` | Number of metric data points kept in memory |
| `METRICS_INTERVAL` | No | `10` | Seconds between metric collections |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `DB_PATH` | No | `data/bot.db` | Path to SQLite database |
| `EXEC_WHITELIST` | No | _(empty)_ | Comma-separated allowed commands. Empty = allow all |
| `EXEC_BLACKLIST` | No | `rm -rf /,mkfs,dd if=/dev/zero` | Always-blocked command patterns |

---

## Running as a Service

To run the bot automatically on boot using systemd:

### 1. Copy the service file

```bash
sudo cp pibot.service /etc/systemd/system/pibot.service
```

### 2. Edit paths if needed

```bash
sudo nano /etc/systemd/system/pibot.service
```

Make sure `WorkingDirectory`, `ExecStart`, and `EnvironmentFile` all point to your actual install location.

### 3. Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable pibot
sudo systemctl start pibot
```

### 4. Check status and logs

```bash
sudo systemctl status pibot
journalctl -u pibot -f
```

---

## Commands

### System

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | List all commands |
| `/dashboard` | Interactive control panel |
| `/info` | Full system overview |
| `/cpu` | CPU usage per core and load average |
| `/ram` | RAM and swap usage |
| `/disk` | Disk usage per partition |
| `/uptime` | System uptime |
| `/temperature` | CPU temperature with status |
| `/healthscore` | Overall Pi health score (0–100) |

### Network

| Command | Description |
|---|---|
| `/ip` | IP addresses for all interfaces |
| `/netinfo` | Network interface stats |
| `/ping <host>` | Ping a host |
| `/wifi` | Scan nearby WiFi networks |
| `/speedtest` | Internet speed test |
| `/portscan <host> [range]` | Scan open ports on a host |

### Power & Services

| Command | Description |
|---|---|
| `/reboot` | Reboot the Pi (asks for confirmation) |
| `/shutdown` | Shut down the Pi (asks for confirmation) |
| `/service <name> <action>` | `start`, `stop`, `restart`, `status`, `enable`, `disable` a service |
| `/services` | List all running systemd services |

### Remote Execution

| Command | Description |
|---|---|
| `/exec <command>` | Run a shell command |
| `/ps` | Top 20 processes by CPU usage |
| `/kill <pid>` | Send SIGTERM to a process |

### Files

| Command | Description |
|---|---|
| `/ls [path]` | List directory (default: `/home/pi`) |
| `/cat <path>` | Read a file's contents |
| `/download <path>` | Send a file to Telegram |
| _(send a file)_ | Upload a file to the Pi at `/tmp/telegram_uploads/` |

### GPIO & Hardware

| Command | Description |
|---|---|
| `/gpio <pin> <on\|off>` | Set a GPIO pin HIGH or LOW |
| `/pwm <pin> <0-100>` | Set PWM duty cycle on a pin |
| `/servo <pin> <0-180>` | Move a servo to an angle |
| `/i2c` | Scan I2C bus for connected devices |
| `/sensors` | Read DHT, BMP280, and CPU thermal sensors |

### Camera

| Command | Description |
|---|---|
| `/snapshot` | Take a photo and send it |
| `/motion <on\|off>` | Toggle motion detection with auto-snapshot |

### Monitoring

| Command | Description |
|---|---|
| `/graph <cpu\|ram\|temp>` | Plot a metric history graph |
| `/alert set <metric> <op> <value>` | Set a resource alert, e.g. `/alert set cpu > 85` |
| `/alert list` | List your active alerts |
| `/alert clear` | Clear all your alerts |
| `/metrics` | Table of last 10 metric readings |

### AI

| Command | Description |
|---|---|
| `/ai <question>` | Ask the AI assistant anything |

### Scheduler

| Command | Description |
|---|---|
| `/schedule <HH:MM> <command>` | Schedule a command to run daily at a time |
| `/cron list` | List scheduled tasks |
| `/cron del <id>` | Delete a scheduled task |

### Notes

| Command | Description |
|---|---|
| `/note add <text>` | Save a note |
| `/note list` | List your notes |
| `/note del <id>` | Delete a note |

### Packages

| Command | Description |
|---|---|
| `/pkg search <name>` | Search APT packages |
| `/pkg install <name>` | Install a package |
| `/pkg remove <name>` | Remove a package |
| `/pkg update` | Run `apt update` |

### Misc

| Command | Description |
|---|---|
| `/backup [paths...]` | Create a `.tar.gz` backup and send it |
| `/weather [city]` | Current weather (auto-detects city from IP if omitted) |

---

## File Structure

```
Raspberry_pi_telegram_bot/
│
├── main.py                  # Entry point — registers all handlers
├── config.py                # Loads all settings from .env
├── requirements.txt         # Python dependencies
├── pibot.service            # systemd service file
├── .env.example             # Environment variable template
├── .env                     # Your local config (never commit this)
│
├── handlers/
│   ├── core.py              # /start, /help, /dashboard
│   ├── system.py            # /info, /cpu, /ram, /disk, /uptime, /temperature, /healthscore
│   ├── network.py           # /ip, /netinfo, /ping, /wifi, /speedtest, /portscan
│   ├── power.py             # /reboot, /shutdown, /service, /services
│   ├── exec_handler.py      # /exec
│   ├── files.py             # /ls, /cat, /download, upload handler
│   ├── gpio_handler.py      # /gpio, /pwm, /servo, /i2c
│   ├── camera.py            # /snapshot, /motion
│   ├── monitoring.py        # /graph, /alert, /metrics
│   ├── ai_handler.py        # /ai
│   ├── scheduler.py         # /schedule, /cron, background scheduler loop
│   ├── notes.py             # /note
│   ├── packages.py          # /pkg
│   ├── backup.py            # /backup
│   ├── weather.py           # /weather
│   ├── sensors.py           # /sensors
│   ├── process.py           # /ps, /kill
│   └── callbacks.py         # Inline keyboard callback router
│
├── utils/
│   ├── auth.py              # Authorization middleware and rate limiter
│   ├── logger.py            # SQLite audit logger
│   ├── metrics.py           # Background metrics collector
│   └── pi_info.py           # Legacy system utility functions
│
└── data/                    # Created at runtime
    ├── bot.db               # SQLite database (audit log, notes, scheduler)
    └── bot.log              # Log file
```

---

## Security

- **Authorization** — `AUTHORIZED_USERS` in `.env` is a whitelist of Telegram user IDs. Anyone not on the list gets an "Access denied" message.
- **Rate limiting** — Each authorized user is limited to `RATE_LIMIT_PER_MINUTE` commands per minute (default 20).
- **Exec safety** — `/exec` checks every command against `EXEC_BLACKLIST`. You can also set `EXEC_WHITELIST` to only allow specific commands.
- **File access** — `/ls`, `/cat`, `/download` only allow access under `/home`, `/var/log`, `/etc`, `/tmp`, and `/opt`.
- **Secrets** — Keep your `.env` file private. It is gitignored by default and should never be committed.
- **Reboot / shutdown** — Both commands require an inline confirmation button before executing.

---

## Contributing

Contributions are welcome! Please fork this repository and submit a pull request with your improvements or bug fixes.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

Developed with ❤️ by [GraveEaterMadison](https://github.com/GraveEaterMadison)
