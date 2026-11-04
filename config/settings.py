PROJECT_NAME = "ShadowPain Dashboard"
VERSION = "1.0.0"
OUTPUT_DIR = "output"

# Настройки Sherlock
SHERLOCK_SITES = "all"  # или конкретные: "github","twitter","instagram"

# Настройки Hashcat
HASHCAT_ATTACK_MODE = "0"  # 0=straight, 1=combination, 3=brute-force
HASHCAT_RULE = "?b"

# Настройки Tor
TOR_PORT = 9050
TOR_CONTROL_PORT = 9051

# Настройки Email
EMAIL_API_BASE = "https://api.mail.tm"

# Portable-режим
PORTABLE_DIR = "portable"
PORTABLE_MODE = False
TOOLS_DIR = "portable"
DATA_DIR = "data"
LOGS_DIR = "logs"

# WSL-настройки
WSL_DISTRO = "Ubuntu"
WSL_WIFI_TOOLS = ["wifite2", "airodump-ng", "aircrack-ng", "airmon-ng"]
