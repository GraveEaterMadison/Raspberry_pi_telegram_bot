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
- [AI & Extensibility](#ai--extensibility)
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
- **Smart Chat Routing** — Just talk to the bot in plain language; Claude Haiku decides whether to chat back or run one of the commands below itself, using cheap tool-use + prompt caching to keep token costs minimal
- **Skill Plugins** — Drop a new file in `skills/` to give the AI a brand-new capability, no other code changes needed
- **Repo Integration** — `/integrate <github-url>` clones a repo you like, has Claude write a skill wrapper for it, and activates it once you confirm — the AI grows its own toolset over time
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
| `AI_PROVIDER` | No | `anthropic` | `anthropic` or `openai` (fallback for `/ai` only) |
| `ANTHROPIC_API_KEY` | No | — | Powers `/ai` and smart chat routing (get at console.anthropic.com) |
| `OPENAI_API_KEY` | No | — | Fallback for `/ai` only, if no Anthropic key is set |
| `AI_MODEL` | No | `claude-haiku-4-5-20251001` | Claude model for `/ai` and smart chat — keep the cheapest Haiku model unless you need more reasoning power |
| `AI_MAX_TOKENS` | No | `400` | Caps Claude's reply length (tokens) per call |
| `AI_SMART_CHAT` | No | `true` | If `true`, every plain chat message is routed through the AI, which can chat back or run a command |
| `AI_EXCLUDED_COMMANDS` | No | _(empty)_ | Comma-separated commands to hide from the AI, e.g. `exec,kill` |
| `VENDOR_DIR` | No | `data/vendor` | Where `/integrate` clones repositories |
| `AI_INTEGRATION_MAX_TOKENS` | No | `2000` | Token budget for the one-off `/integrate` code-generation call |
| `INTEGRATION_CLONE_TIMEOUT` | No | `90` | Max seconds for `/integrate` to clone a repo |
| `INTEGRATION_INSTALL_TIMEOUT` | No | `180` | Max seconds for `/integrate` to install a confirmed repo's dependencies |
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
| _(any plain message)_ | Talk to the bot naturally — Claude decides whether to reply or run a command for you, see [AI & Extensibility](#ai--extensibility) |
| `/integrate <github-url>` | Turn a GitHub repo into a new AI skill (asks for confirmation first) |

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

## AI & Extensibility

Set `ANTHROPIC_API_KEY` and every plain message you send the bot (no leading `/`) is handled by Claude Haiku — the cheapest current Claude model. It either answers directly, like a normal chat, or picks one of the bot's ~45 commands and runs it for you (e.g. "how hot is the Pi right now?" → runs `/temperature`; "turn on GPIO 18" → runs `/gpio 18 on`).

**Why it stays cheap:**
- Uses `claude-haiku-4-5-20251001` by default (configurable via `AI_MODEL`).
- The system prompt and full tool list are marked for [prompt caching](https://docs.anthropic.com/), so they're billed at full price only once every few minutes — every message after that pays the much cheaper cached-read rate.
- Exactly **one** Claude API call per message, always. When a command is picked, its own reply *is* the answer — there's no second round-trip to have Claude "summarize" the result.
- `AI_MAX_TOKENS` caps every reply length.
- Turn it off entirely with `AI_SMART_CHAT=false` and keep using `/ai <question>` only.

**Safety:** every command keeps its existing behavior. `/reboot` and `/shutdown` still show their own inline "are you sure?" confirmation button no matter who (or what) triggers them, so the AI can't reboot or shut down the Pi without a human tapping confirm. If you want to keep other commands (like `/exec` or `/kill`) out of the AI's hands entirely, list them in `AI_EXCLUDED_COMMANDS`.

**Adding new capabilities:** drop a new file into `skills/` — no other code changes needed. Each file defines a `SKILL` dict with a `name`, `description`, and an async `handler`. See [`skills/time_skill.py`](skills/time_skill.py) for a minimal working example, and the docstring in [`skills/__init__.py`](skills/__init__.py) for the full shape. Skills can either return a plain string (`kind: "data"`) or reply to Telegram themselves like any other command handler (`kind: "action"`).

**Integrating someone else's GitHub project:** `/integrate https://github.com/owner/repo` shallow-clones the repo into `VENDOR_DIR`, sends its README/file listing/manifest to Claude, and gets back a single `skills/`-shaped Python module wrapping it. The bot then shows you a summary, the detected tool name(s), the exact dependency-install command it would run (if any), and the generated code as a downloadable file — nothing is installed or activated yet. Only after you tap **✅ Aktivieren** does it install dependencies and copy the file into `skills/`, which immediately hot-reloads the AI's tool catalogue; **❌ Verwerfen** deletes the clone instead.

This intentionally always requires a human in the loop: `/integrate` is excluded from the AI's own auto-triggered tool-calling (see `ai/registry.py`), so mentioning a GitHub link in normal chat never starts this by itself — you always have to run the command yourself. Since it runs arbitrary third-party code with the bot's full privileges (shell, files, GPIO), only integrate repos you trust, and actually read the generated code before confirming.

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
│   ├── ai_handler.py        # /ai, smart chat routing
│   ├── integrate_handler.py # /integrate
│   ├── scheduler.py         # /schedule, /cron, background scheduler loop
│   ├── notes.py             # /note
│   ├── packages.py          # /pkg
│   ├── backup.py            # /backup
│   ├── weather.py           # /weather
│   ├── sensors.py           # /sensors
│   ├── process.py           # /ps, /kill
│   └── callbacks.py         # Inline keyboard callback router
│
├── ai/
│   ├── registry.py          # Builds the Claude tool catalogue from COMMANDS + skills/
│   ├── agent.py             # One Claude call per message: chat back or run a tool
│   └── integrator.py        # /integrate: clone a repo, generate + confirm a skill wrapper
│
├── skills/                  # Drop-in AI capabilities — see AI & Extensibility
│   └── time_skill.py        # Example skill
│
├── utils/
│   ├── auth.py              # Authorization middleware and rate limiter
│   ├── logger.py            # SQLite audit logger
│   ├── metrics.py           # Background metrics collector
│   └── pi_info.py           # Legacy system utility functions
│
└── data/                    # Created at runtime
    ├── bot.db               # SQLite database (audit log, notes, scheduler)
    ├── bot.log              # Log file
    └── vendor/              # Repos cloned by /integrate
```

---

## Security

- **Authorization** — `AUTHORIZED_USERS` in `.env` is a whitelist of Telegram user IDs. Anyone not on the list gets an "Access denied" message.
- **Rate limiting** — Each authorized user is limited to `RATE_LIMIT_PER_MINUTE` commands per minute (default 20).
- **Exec safety** — `/exec` checks every command against `EXEC_BLACKLIST`. You can also set `EXEC_WHITELIST` to only allow specific commands.
- **File access** — `/ls`, `/cat`, `/download` only allow access under `/home`, `/var/log`, `/etc`, `/tmp`, and `/opt`.
- **Secrets** — Keep your `.env` file private. It is gitignored by default and should never be committed.
- **Reboot / shutdown** — Both commands require an inline confirmation button before executing.
- **`/integrate`** — Never auto-triggered by the AI; generated code is syntax-checked and shown to you (summary + downloadable source) before anything is installed or activated, and only after you tap confirm. It still runs arbitrary third-party code with the bot's full privileges, so only integrate repositories you trust.

---

## Contributing

Contributions are welcome! Please fork this repository and submit a pull request with your improvements or bug fixes.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

Developed with ❤️ by [GraveEaterMadison](https://github.com/GraveEaterMadison)
