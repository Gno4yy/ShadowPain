"""
Portable Module — Скачивание и распаковка portable-версий инструментов
Позволяет использовать ShadowPain на чужом компьютере без прав админа
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import tarfile
import platform

# Добавляем корень проекта в путь при запуске напрямую
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from utils.helpers import (
    clear_screen, print_banner, print_success, print_error,
    print_info, print_warning, run_command, check_tool, safe_input
)
from utils.logger import setup_logger

logger = setup_logger()


DOWNLOADS_DIR = "portable"


def run_portable_module():
    """Модуль portable-инструментов"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === Portable — Инструменты без установки ===\n")
        print("  Скачивает portable-версии в папку portable/")
        print("  Работает без прав администратора!\n")
        print("  [1]  Скачать Hashcat")
        print("  [2]  Скачать Tor Browser")
        print("  [3]  Скачать Wireshark Portable")
        print("  [4]  Установить Sherlock (OSINT)")
        print("  [5]  Установить Spiderfoot (OSINT)")
        print("  [6]  Установить Blackbird (OSINT)")
        print("  [7]  Установить Holehe (OSINT)")
        print("  [8]  Установить GHunt (OSINT)")
        print("  [9]  Показать статус всех инструментов")
        print("  [10] Инструкция по WiFi-флешке")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            download_hashcat()
        elif choice == "2":
            download_tor()
        elif choice == "3":
            download_wireshark()
        elif choice == "4":
            pip_portable()
        elif choice == "5":
            install_spiderfoot()
        elif choice == "6":
            install_blackbird()
        elif choice == "7":
            install_holehe()
        elif choice == "8":
            install_ghunt()
        elif choice == "9":
            show_portable_status()
        elif choice == "10":
            show_linux_usb_guide()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            input("  [Enter для продолжения...]")


def ensure_downloads_dir():
    """Создаёт папку portable/"""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    return DOWNLOADS_DIR


def download_file(url, dest, description=""):
    """Скачивание файла с прогрессом"""
    if description:
        print_info(f"Скачивание: {description}")
    
    try:
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(downloaded * 100 / total_size, 100)
            sys.stdout.write(f'\r  [{'#' * int(percent/2)}{' ' * (50 - int(percent/2))}] {percent:.0f}%')
            sys.stdout.flush()
        
        urllib.request.urlretrieve(url, dest, progress)
        sys.stdout.write('\n')
        return True
    except Exception as e:
        print_error(f" Ошибка скачивания: {e}")
        return False


def download_hashcat():
    """Скачивание Hashcat"""
    print_info("Скачивание Hashcat...\n")
    
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    system = platform.system()
    
    if system == "Windows":
        # Hashcat для Windows
        print_info("Скачиваем Hashcat для Windows...\n")
        
        print_warning("Hashcat для Windows скачивается вручную:")
        print_info("  https://hashcat.net/hashcat/\n")
        
        choice = input("  Скачать через браузер? (y/n): ").strip().lower()
        if choice == "y":
            subprocess.run("start https://hashcat.net/hashcat/", shell=True)
            print_info("\n 1. Распакуйте в portable/hashcat/")
            print_info(" 2. Hashcat — portable, не требует установки!")
        
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Linux
    print_info("Скачиваем Hashcat для Linux...\n")
    print_warning("Hashcat для Linux скачивается вручную:")
    print_info("  https://hashcat.net/hashcat/\n")
    
    choice = input("  Открыть страницу скачивания? (y/n): ").strip().lower()
    if choice == "y":
        subprocess.run("start https://hashcat.net/hashcat/", shell=True)
        print_info("\n 1. Распакуйте в portable/hashcat/")
        print_info(" 2. Hashcat — portable, не требует установки!")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Downloaded Hashcat")


def download_tor():
    """Скачивание Tor Browser"""
    print_info("Скачивание Tor Browser...\n")
    
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    print_warning("Tor Browser весит ~80MB. Скачиваем через браузер:")
    print_info("  https://www.torproject.org/download/\n")
    
    choice = input("  Открыть страницу скачивания? (y/n): ").strip().lower()
    if choice == "y":
        subprocess.run("start https://www.torproject.org/download/", shell=True)
        print_info("\n  Распакуйте в portable/tor/")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Downloaded Tor Browser")


def download_wireshark():
    """Скачивание Wireshark Portable"""
    print_info("Скачивание Wireshark...\n")
    
    print_warning("Wireshark не имеет portable-версии.\n")
    print_info("Альтернативы:\n")
    print("  1. tshark CLI (часть Wireshark):")
    print("     → https://www.wireshark.org/download.html")
    print("     → Скачайте Wireshark — tshark уже внутри\n")
    print("  2. Используйте WSL:")
    print("     → sudo apt install tshark\n")
    
    choice = input("  Открыть страницу скачивания? (y/n): ").strip().lower()
    if choice == "y":
        subprocess.run("start https://www.wireshark.org/download.html", shell=True)
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Wireshark download page opened")


def pip_portable():
    """Установка Python-пакетов в пользовательскую директорию через git"""
    print_info("Установка Python-пакетов в portable-режиме через git...\n")
    print_info("Пакеты установятся в папку portable/ без прав админа.\n")
    
    # Устанавливаем sherlock через git
    print_info("Устанавливаем Sherlock через git...")
    run_command('git clone https://github.com/sherlock-project/sherlock.git portable/sherlock')
    cmd = f'pip install --break-system-packages --target portable/lib portable/sherlock'
    stdout, stderr, rc = run_command(cmd)
    
    if rc == 0:
        print_success("  Sherlock установлен")
    else:
        print_error(f"  Sherlock — ошибка: {stderr[:100]}")
    
    # Создаём portable-скрипт запуска
    launcher = '''@echo off
set PYTHONPATH=%~dp0portable\\lib
set PATH=%~dp0portable\\Lib;%PATH%
python main.py
pause
'''
    launcher_path = os.path.join(os.getcwd(), "ShadowPain_Portable.bat")
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(launcher)
    
    print()
    print_success(" Python-пакеты установлены!")
    print_info(f" Скрипт: {launcher_path}")
    print_info(" Используйте ShadowPain_Portable.bat для запуска!")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Installed pip packages in portable mode")


def install_spiderfoot():
    """Установка Spiderfoot — OSINT-сканер"""
    print_info("Установка Spiderfoot...\n")
    print_info("Spiderfoot — 200+ модулей OSINT (email, IP, домен, никнейм)\n")
    print_info("Spiderfoot требует систему сборки (gcc, libxml2-dev). Устанавливаем через pip...\n")
    
    # Сначала системные зависимости
    print_info("Шаг 1: Системные зависимости (если Linux)...\n")
    run_command('sudo apt install -y libxml2-dev libxslt1-dev python3-dev')
    
    print_info("Шаг 2: Установка через pip...\n")
    stdout, stderr, rc = run_command(f'{sys.executable} -m pip install --break-system-packages spiderfoot')
    
    if rc == 0:
        print_success("  Spiderfoot установлен!")
        print_info(f"  Запуск: spiderfoot -l 127.0.0.1:5001\n")
    else:
        print_error(f"  Ошибка: {stderr[:300]}")
        print_info("  Альтернатива: git clone https://github.com/smicallef/spiderfoot.git")
        print_info("  cd spiderfoot && pip install -r requirements.txt\n")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Installed Spiderfoot")


def install_blackbird():
    """Установка Blackbird — быстрый поиск по никнейму"""
    print_info("Установка Blackbird...\n")
    print_info("Blackbird — быстрый поиск никнейма через 150+ платформ с Tor\n")
    
    print_info("Клонирую репозиторий...\n")
    stdout, stderr, rc = run_command('git clone https://github.com/antoniaci/blackbird.git')
    
    if rc == 0:
        print_success("  Репозиторий клонирован!")
        print_info(f"\n  Установка зависимостей...\n")
        stdout, stderr, rc = run_command(f'{sys.executable} -m pip install --break-system-packages ./blackbird')
        
        if rc == 0:
            print_success("  Blackbird установлен!")
            print_info(f"  Запуск: blackbird <username>\n")
        else:
            print_error(f"  Зависимости: {stderr[:300]}")
    else:
        print_error(f"  Ошибка клонирования: {stderr[:300]}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Installed Blackbird")


def install_holehe():
    """Установка Holehe — проверка email на регистрацию в 120+ сервисах"""
    print_info("Установка Holehe...\n")
    print_info("Holehe — проверка email на регистрацию в сервисах (Facebook, Instagram, Twitter...)\n")
    
    print_info("Клонирую репозиторий...\n")
    stdout, stderr, rc = run_command('git clone https://github.com/megadose/holehe.git')
    
    if rc == 0:
        print_success("  Репозиторий клонирован!")
        print_info(f"\n  Установка зависимостей...\n")
        stdout, stderr, rc = run_command(f'{sys.executable} -m pip install --break-system-packages ./holehe')
        
        if rc == 0:
            print_success("  Holehe установлен!")
            print_info(f"  Запуск: holehe <email>\n")
        else:
            print_error(f"  Зависимости: {stderr[:300]}")
    else:
        print_error(f"  Ошибка клонирования: {stderr[:300]}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Installed Holehe")


def install_ghunt():
    """Установка GHunt — сбор информации из Google"""
    print_info("Установка GHunt...\n")
    print_info("GHunt — сбор информации из Google (аккаунт, Maps, Photos)\n")
    print_warning("  ⚠  Требуется авторизация Google (OAuth2)!\n")
    
    print_info("Клонирую репозиторий...\n")
    stdout, stderr, rc = run_command('git clone https://github.com/mxrch/GHunt.git')
    
    if rc == 0:
        print_success("  Репозиторий клонирован!")
        print_info(f"\n  Установка зависимостей...\n")
        stdout, stderr, rc = run_command(f'{sys.executable} -m pip install --break-system-packages ./GHunt')
        
        if rc == 0:
            print_success("  GHunt установлен!")
            print_info(f"  Запуск: ghunt email <email>\n")
            print_info("  Первичная настройка: python GHunt/ghunt.py --init\n")
        else:
            print_error(f"  Зависимости: {stderr[:300]}")
    else:
        print_error(f"  Ошибка клонирования: {stderr[:300]}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Installed GHunt")


def show_portable_status():
    """Показывает статус всех portable-инструментов"""
    clear_screen()
    print_banner()
    print("\n  === Статус Portable-инструментов ===\n")
    
    status = {
        "Sherlock": ("pip install sherlock-project", True),
        "Spiderfoot": ("pip install spiderfoot", False),
        "Blackbird": ("git clone + pip install", False),
        "Holehe": ("git clone + pip install", False),
        "GHunt": ("git clone + pip install (OAuth2)", False),
        "Анонимная почта": ("Встроено (Mail.tm API)", True),
        "Hashcat": ("Скачать portable: hashcat.net", False),
        "Wireshark": ("Скачать: wireshark.org", False),
        "Tor": ("Скачать: torproject.org", False),
        "Wifite": ("Требует WSL или Linux-флешку", False),
    }
    
    print("  Инструмент          | Статус")
    print("  ────────────────────┼────────────────────────────────")
    
    for name, (install, builtin) in status.items():
        if builtin:
            print(f"  \033[92m[✓]\033[0m  {name:20s} — уже работает")
        else:
            print(f"  \033[93m[!]\033[0m  {name:20s} — {install}")
    
    print()
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Checked portable status")


def show_linux_usb_guide():
    """Показывает инструкцию по созданию Linux-флешки для WiFi"""
    guide = """
  ╔══════════════════════════════════════════════════════════╗
  ║  Linux-флешка для WiFi-аудита (портативный Kali)         ║
  ╠══════════════════════════════════════════════════════════╣
  ║                                                          ║
  ║  Для WiFi-аудита на чужом ПК нужен Linux с поддержкой    ║
  ║  monitor mode WiFi-карты.                                ║
  ║                                                          ║
  ║  1.  Скачать Kali Live USB:                              ║
  ║      → https://www.kali.org/get-kali/                    ║
  ║      → Kali Live USB (не устанавливается!)               ║
  ║                                                          ║
  ║  2.  Записать на флешку:                                 ║
  ║      → Скачать Rufus: https://rufus.ie/                  ║
  ║      → Выбрать ISO Kali → Записать                       ║
  ║                                                          ║
  ║  3.  Загрузиться с флешки:                               ║
  ║      → Вставить флешку → Перезагрузить                   ║
  ║      → В BIOS выбрать USB-загрузку                       ║
  ║      → Kali Live → Try Kali                              ║
  ║                                                          ║
  ║  4.  WiFi-аудит:                                         ║
  ║      → wifite                                            ║
  ║      → airodump-ng                                       ║
  ║      → Все инструменты уже есть!                         ║
  ║                                                          ║
  ║  5.  ShadowPain на флешке:                               ║
  ║      → Скопировать папку проекта на флешку               ║
  ║      → python main.py                                    ║
  ║      → Всё работает!                                     ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
    """
    print(guide)
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Showed Linux USB guide")
