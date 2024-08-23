# Raspberry Pi Telegram Bot

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi%4-Model%20B-orange)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A versatile Telegram bot that runs on a Raspberry Pi, allowing you to control your Pi and interact with it remotely via Telegram. This project is designed to help you automate tasks, gather system information, and manage your Raspberry Pi from anywhere.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Commands](#commands)
- [File Structure](#file-structure)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Features

- **Remote Access**: Control your Raspberry Pi remotely via Telegram.
- **System Monitoring**: Fetch real-time system information such as CPU usage, memory stats, and disk space.
- **Automation**: Set up custom commands to automate various tasks.
- **Modular Design**: Easily extend functionality by adding new modules to the bot.
- **Secure**: Uses Telegram's secure API for bot communication, with customizable access controls.

## Installation

### Prerequisites

- A Raspberry Pi running a Debian-based OS (e.g., Raspbian).
- Python 3.x installed.
- A Telegram account to create a bot.

### Steps

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/GraveEaterMadison/Raspberry_pi_telegram_bot.git
    cd Raspberry_pi_telegram_bot
    ```

2. **Install Required Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Create a Telegram Bot**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram.
   - Use the `/newbot` command to create your bot and get the API token.

4. **Configure the Bot**:
   - Copy the `config_sample.py` file to `config.py` and add your bot token and other configuration details.

5. **Run the Bot**:
    ```bash
    python bot.py
    ```

## Configuration

Edit the `config.py` file to set your bot's configuration. Here's a breakdown of the essential settings:

- **TOKEN**: Your Telegram bot token provided by BotFather.
- **AUTHORIZED_USERS**: A list of Telegram user IDs allowed to interact with the bot.
- **LOGGING**: Configure the logging level and output.

```python
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
AUTHORIZED_USERS = [123456789, 987654321]
LOGGING = {
    'level': 'INFO',
    'file': 'bot.log'
}
```

## Usage

Once the bot is up and running, you can start sending commands via Telegram. The bot will respond with the requested information or perform the specified task.

### Example Commands

Here are some example commands you can use:

- **Start the bot**:
  ```text
  /start
  ```

- **List all available command**:
  ```text
  /help
  ```

- **Reboot the Raspberry Pi**:
  ```text
  /reboot
  ```

- **Shutdown the Raspberry Pi**:
  ```twxt
  /shutdown
  ```
  
- **Check CPU usage**:
  ```text
  /cpu
  ```

- **Check memory usage**:
   ```text
  /memory
  ```

- **Check disk space**:
   ```text
  /disk
  ```

- **Turn on an LED connected to GPIO pin**:
   ```text
  /gpio on
   ```
- **Turn off an LED connected to GPIO pin**:
   ```text
  /gpio oFF
   ```
### Commands

You can add more commands by modifying the bot.py file and defining new functions to handle those commands.

### File Structure

```bash
Raspberry_pi_telegram_bot/
│
├── bot.py              # Main bot script
├── config_sample.py    # Sample configuration file
├── requirements.txt    # Python dependencies
├── README.md           # This README file
└── LICENSE             # License file
```

### Contributing

Contributions are welcome! Please fork this repository and submit a pull request with your improvements or bug fixes.

### License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/GraveEaterMadison/Raspberry_pi_telegram_bot/blob/main/LICENSE) file for details.

### Acknowledgements

This project was inspired by various online resources and tutorials that guide the creation of Raspberry Pi-based Telegram bots.

You can add custom commands by creating new handlers in the handlers/ directory.

Developed with ❤️ by [GraveEaterMadison](https://github.com/GraveEaterMadison)
```vbnet

You can copy and paste this content into your `README.md` file under the relevant sections. Let me know if you need further adjustments!
```
