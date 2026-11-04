# ShadowPain Dashboard — Pentest & OSINT Framework

Многофайловая обёртка-дашборд для пентеста и OSINT-исследований.

## Возможности

- **OSINT** — поиск по никнейму через Sherlock (поиск аккаунтов в соцсетях)
- **WiFi** — аудит WiFi-сетей через Wifite
- **Hash** — работа с хешами через Hashcat
- **Tor** — настройка и проверка Tor-трафика
- **Email** — создание анонимной почты через Mail.tm API

## Установка

```bash
pip install -r requirements.txt
```

Убедитесь, что системные утилиты установлены:
- `sherlock` — `pip install sherlock-project`
- `wifite` — `apt install wifite2` или `pip install wifite2`
- `hashcat` — https://hashcat.net/hashcat/

## Запуск

```bash
python main.py
```

## ⚠️ Дисклеймер

Этот инструмент предназначен **только для образовательных целей и тестирования
собственных сетей/ресурсов**. Использование против систем без разрешения —
незаконно.

## Структура проекта

```
├── main.py                 # Главный файл, CLI-меню
├── config/
│   ├── __init__.py
│   └── settings.py         # Настройки проекта
├── modules/
│   ├── __init__.py
│   ├── osint.py            # Sherlock, OSINT-модуль
│   ├── wifi.py             # Wifite, WiFi-аудит
│   ├── hash.py             # Hashcat, работа с хешами
│   ├── tor.py              # Tor, анонимность
│   └── email.py            # Анонимная почта
├── utils/
│   ├── __init__.py
│   ├── logger.py           # Логирование
│   └── helpers.py          # Вспомогательные функции
├── output/                 # Папка для результатов
└── requirements.txt
```
