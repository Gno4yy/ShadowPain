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

## Установка

### Windows

**1. Установить Python 3.10+**

Скачайте с [python.org](https://www.python.org/downloads/) → обязательно поставьте галочку **«Add Python to PATH»**.

**2. Установить зависимости**

```powershell
# Клонируем проект
git clone https://github.com/Gno4yy/ShadowPain
cd ShadowPain

# Устанавливаем Python-пакеты
pip install -r requirements.txt

# Или вручную:
pip install requests PySocks prettytable tldextract sherlock-project sqlmap
```

**3. Системные утилиты (опционально)**

| Утилита | Для чего | Установка |
|---------|----------|-----------|
| `hashcat` | Взлом хешей | Скачать с [hashcat.net](https://hashcat.net/hashcat/) |
| `tshark` | Анализ трафика | Скачать Wireshark с [wireshark.org](https://www.wireshark.org/download.html) |
| `tor` | Анонимность | Скачать с [torproject.org](https://www.torproject.org/download/) |
| `wsl` | WiFi-аудит | `wsl --install` (PowerShell от админа) |

**4. Запуск**

```powershell
python main.py
# или через Setup → [7] Setup → [1] Автоустановка всего
```

---

### Linux (Ubuntu/Debian/Kali)

**1. Установить Python 3.10+ и pip**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# Kali
# Python3 уже установлен
```

**2. Установить зависимости**

```bash
# Клонируем проект
git clone <repo>
cd "gno4yy project"

# Устанавливаем Python-пакеты
pip3 install -r requirements.txt

# Или вручную:
pip3 install requests PySocks prettytable tldextract sherlock-project sqlmap
```

**3. Системные утилиты (опционально)**

| Утилита | Для чего | Установка |
|---------|----------|-----------|
| `hashcat` | Взлом хешей | `sudo apt install hashcat` или [hashcat.net](https://hashcat.net/hashcat/) |
| `tshark` | Анализ трафика | `sudo apt install tshark` или Wireshark с [wireshark.org](https://www.wireshark.org/download.html) |
| `tor` | Анонимность | `sudo apt install tor` или [torproject.org](https://www.torproject.org/download/) |

**4. Запуск**

```bash
python3 main.py
# или через Setup → [7] Setup → [1] Автоустановка всего
```

---

### Portable-режим (на чужом ПК)

Если нет прав администратора или нельзя устанавливать Python:

1. Скачайте portable-версии инструментов (Hashcat, Wireshark Portable и т.д.)
2. Распакуйте в папку `portable/`
3. Запустите → [7] Setup → [5] Настроить portable-режим

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
