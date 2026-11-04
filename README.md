# ShadowPain Dashboard — Pentest & OSINT Framework

Многофайловая CLI-обёртка-дашборд для пентеста, OSINT-исследований и анализа безопасности.

## Возможности

| № | Модуль | Описание |
|---|--------|----------|
| 1 | **OSINT** | Поиск по никнейму — **97 сайтов** (соцсети, форумы, игры, крипто, блоги, маркетплейсы) |
| 2 | **WiFi** | Аудит WiFi-сетей через Wifite / airodump-ng (WSL) |
| 3 | **Hash** | Взлом / проверка хешей через Hashcat (словарь, brute-force, автоопределение режима) |
| 4 | **Tor** | Проверка IP, ротация идентичности, настройка SOCKS-прокси |
| 5 | **Email** | Анонимная почта Mail.tm — создание, входящие, чтение, SMTP-отправка |
| 6 | **Network** | Анализ трафика через tshark/Wireshark (захват, фильтры, DNS, HTTP) |
| 7 | **Setup** | Автоустановка инструментов, проверка окружения, WSL, portable-режим |
| 8 | **Portable** | Portable-версии инструментов (без прав админа) |
| 9 | **SQLMap** | Тестирование SQL-инъекций (GET, POST, cookies, автоэксплуатация, сканер из файла) |
| 10 | **Output** | Управление файлами результатов (просмотр, удаление по номеру/паттерну, очистка) |

## Быстрый старт

```bash
# 1. Клонировать
git clone <repo>
cd "gno4yy project"

# 2. Запустить
python main.py

# 3. Или через Setup (автоустановка)
# Пункт [7] Setup → [1] Автоустановка всего
```

## Установка зависимостей

```bash
# Основные Python-пакеты
pip install requests PySocks prettytable tldextract

# Sherlock (OSINT)
pip install sherlock-project

# SQLMap
pip install sqlmap
```

## Системные утилиты (опционально)

| Утилита | Для чего | Установка |
|---------|----------|-----------|
| `hashcat` | Взлом хешей | https://hashcat.net/hashcat/ |
| `tshark` | Анализ трафика | https://www.wireshark.org/download.html |
| `sqlmap` | SQL-инъекции | `pip install sqlmap` |
| `wsl` | WiFi-аудит | `wsl --install` (PowerShell) |
| `tor` | Анонимность | https://www.torproject.org/download/ |

## Структура проекта

```
├── main.py                     # Главный файл, CLI-меню
├── config/
│   ├── __init__.py
│   └── settings.py             # Настройки проекта
├── modules/
│   ├── __init__.py
│   ├── osint.py                # 97 сайтов, Sherlock + quick_search
│   ├── wifi.py                 # Wifite, airodump-ng (WSL)
│   ├── hash.py                 # Hashcat (словарь, brute-force)
│   ├── tor.py                  # IP, ротация, прокси
│   ├── mail.py                 # Mail.tm API + SMTP-отправка
│   ├── wireshark.py            # tshark (захват, фильтры, pcap)
│   ├── sqlmap.py               # SQL-инъекции (GET/POST/cookies)
│   ├── setup.py                # Автоустановка, проверка, WSL
│   ├── portable.py             # Portable-режим
│   └── output_manager.py       # Управление файлами результатов
├── utils/
│   ├── __init__.py
│   ├── logger.py               # Логирование в output/
│   └── helpers.py              # Баннер, safe_input, save_output
├── output/                     # Папка для результатов
└── requirements.txt
```

## Особенности

- **safe_input** — корректная обработка Ctrl+C / EOF во всех модулях
- **Абсолютные пути** — output-файлы сохраняются независимо от рабочей директории
- **sanitize_filename** — очистка имён файлов от недопустимых символов Windows
- **Автоопределение sqlmap** — находит в PATH, Scripts, site-packages
- **Fallback OSINT** — если Sherlock не установлен, автоматически quick_search через urllib
- **SMTP-отправка** — Gmail, Outlook, Yandex, Mail.ru, ProtonMail + свой SMTP

## ⚠️ Дисклеймер

Этот инструмент предназначен **только для образовательных целей и тестирования
собственных сетей/ресурсов**. Использование против систем без разрешения —
незаконно.
