"""
Setup Module — Автоустановка и проверка всех инструментов
Позволяет использовать ShadowPain на чужом компьютере
"""

import subprocess
import sys
import os
import platform
import shutil

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


def run_setup_module():
    """Модуль настройки и установки инструментов"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === Setup — Настройка инструментов ===\n")
        print("  [1]  Автоустановка всего (рекомендуется)")
        print("  [2]  Проверить что установлено")
        print("  [3]  Установить Python-пакеты")
        print("  [4]  Настроить WSL (для WiFi)")
        print("  [5]  Настроить portable-режим")
        print("  [6]  Сгенерировать скрипт запуска")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            auto_install_all()
        elif choice == "2":
            check_all_installed()
        elif choice == "3":
            install_python_packages()
        elif choice == "4":
            setup_wsl()
        elif choice == "5":
            setup_portable()
        elif choice == "6":
            generate_launcher()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            input("  [Enter для продолжения...]")


def auto_install_all():
    """Автоматическая установка всех инструментов без вопросов"""
    print_info("Начинаю автоматическую установку всех инструментов...\n")
    print_info("Это может занять 5-15 минут. Не закрывайте программу.\n")
    
    # 1. Установка Python-пакетов
    print_info("Шаг 1/4: Установка Python-пакетов...")
    packages_installed = _install_python_packages_auto()
    
    # 2. Установка WSL (если Windows)
    if platform.system() == "Windows":
        print_info("Шаг 2/4: Настройка WSL...")
        wsl_installed = _install_wsl_auto()
    else:
        wsl_installed = True
    
    # 3. Установка WiFi-инструментов в WSL
    if wsl_installed:
        print_info("Шаг 3/4: Установка WiFi-инструментов...")
        wifi_installed = _install_wifi_tools_auto()
    else:
        wifi_installed = False
    
    # 4. Генерация скрипта запуска
    print_info("Шаг 4/4: Генерация скрипта запуска...")
    generate_launcher_auto()
    
    # Итог
    print()
    print_success(" Автоматическая установка завершена!\n")
    print_info(" Что работает сразу:\n")
    print("  ✓ OSINT (Sherlock) — если установлен")
    print("  ✓ Email (Mail.tm) — работает всегда")
    print("  ✓ SQLMap — если установлен")
    print("  ✓ Tor — если установлен")
    print()
    print_info(" Что требует ручной установки:\n")
    print("  • Hashcat — скачать: https://hashcat.net/hashcat/")
    print("  • Wireshark — скачать: https://www.wireshark.org/download.html")
    print("  • Wifite — установлен в WSL (если Windows)")
    print()
    print_info(" Для WiFi-аудита используйте WSL или Linux-флешку.\n")
    
    input("  [Enter для продолжения...]")
    logger.info("Auto installation completed")


def _install_python_packages_auto():
    """Автоматическая установка Python-пакетов"""
    packages = [
        ("requests", False),
        ("PySocks", False),
        ("sherlock-project", True),
        ("wifite2", False),
        ("sqlmap", False),
    ]
    
    installed = 0
    failed = 0
    
    for pkg, critical in packages:
        print_info(f"  Установка {pkg}...")
        stdout, stderr, rc = run_command(f'{sys.executable} -m pip install "{pkg}"')
        
        if rc == 0:
            print_success(f"  ✓ {pkg} установлен")
            installed += 1
        else:
            if critical:
                print_warning(f"  ! {pkg} — ошибка (попробуем без pandas)")
                # Пробуем установить без pandas
                run_command(f'{sys.executable} -m pip uninstall pandas -y 2>nul')
                stdout, stderr, rc = run_command(f'{sys.executable} -m pip install "{pkg}"')
                if rc == 0:
                    print_success(f"  ✓ {pkg} установлен (без pandas)")
                    installed += 1
                else:
                    print_error(f"  ✗ {pkg} — не установлен")
                    failed += 1
            else:
                print_warning(f"  ! {pkg} — не установлен (не критично)")
                failed += 1
    
    print(f"\n  Установлено: {installed}/{len(packages)}")
    return installed == len(packages)


def check_all_installed():
    """Проверка всех необходимых инструментов"""
    clear_screen()
    print_banner()
    print("\n  === Проверка установленных инструментов ===\n")
    
    tools = {
        "Python": ("python", True),
        "pip": ("pip", True),
        "Git": ("git", False),
        "Hashcat": ("hashcat", False),
        "tshark": ("tshark", False),
        "Wireshark": ("wireshark", False),
        "Tor": ("tor", False),
        "WSL": ("wsl", False),
    }
    
    python_packages = [
        "requests",
        "socks",
        "sherlock",
    ]
    
    print("  Системные утилиты:")
    print("  ─────────────────────────────────────────")
    
    all_ok = True
    
    for name, (cmd, required) in tools.items():
        if check_tool(cmd):
            print(f"  \033[92m[✓]\033[0m  {name:20s} — установлен")
        else:
            status = "ОБЯЗАТЕЛЬНО" if required else "Рекомендуется"
            print(f"  \033[91m[✗]\033[0m  {name:20s} — НЕ НАЙДЕН ({status})")
            all_ok = required
    
    print()
    print("  Python-пакеты:")
    print("  ─────────────────────────────────────────")
    
    for pkg in python_packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  \033[92m[✓]\033[0m  {pkg:20s} — установлен")
        except ImportError:
            print(f"  \033[91m[✗]\033[0m  {pkg:20s} — НЕ УСТАНОВЛЕН")
            all_ok = False
    
    print()
    if all_ok:
        print_success(" Все необходимые инструменты установлены!")
    else:
        print_warning(" Некоторые инструменты не установлены. Используйте пункт [2] для установки.")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Checked all installed tools")


def _install_wsl_auto():
    """Автоматическая установка WSL"""
    if not check_tool("wsl"):
        print_info("  Установка WSL...")
        stdout, stderr, rc = run_command("wsl --install -d Ubuntu")
        if rc == 0:
            print_success("  WSL установлен. Перезагрузите компьютер.")
            print_info("  После перезагрузки запустите ShadowPain снова.\n")
            input("  [Enter для продолжения...]")
            return False
        else:
            print_error("  Не удалось установить WSL.")
            return False
    else:
        print_success("  WSL уже установлен.")
        return True


def _install_wifi_tools_auto():
    """Автоматическая установка WiFi-инструментов в WSL"""
    if not check_tool("wsl"):
        print_error("  WSL не установлен. WiFi-инструменты не будут установлены.")
        return False
    
    print_info("  Установка wifite2 и aircrack-ng в WSL...")
    cmd = 'wsl sudo apt update && wsl sudo apt install -y wifite2 aircrack-ng'
    stdout, stderr, rc = run_command(cmd)
    
    if rc == 0:
        print_success("  WiFi-инструменты установлены в WSL!")
        return True
    else:
        print_error("  Не удалось установить WiFi-инструменты.")
        print_info("  Попробуйте вручную: wsl sudo apt install -y wifite2 aircrack-ng\n")
        return False


def generate_launcher_auto():
    """Автоматическая генерация скрипта запуска"""
    launcher = r"""@echo off
chcp 65001 >nul
title ShadowPain Dashboard
cls

echo.
echo   /\ \ \                                 
echo  __     ___     ___\ \ \ \    __  __   __  __   __  __    
echo /'_ `\ /' _ `\  / __`\ \ \ \_ /\ \/\ \ /\ \/\ \ /\ \/\ \   
echo/\ \L\ \/\ \/\ \/\ \L\ \ \__ ,__\ \ \_\ \\ \_\ \\ \_\ \  
echo\ \____ \ \_\ \_\ \____/\/_/\_\_/\/`____ \\/`____ \\/`____ \ 
echo \/___L\ \/_/\/_/\/___/    \/_/   `/___/> \`/___/> \`/___/> \
echo   /\____/                           /\___/   /\___/   /\___/
echo   \_/__/                            \/__/    \/__/    \/__/
echo.
echo   ShadowPain Dashboard — Быстрый запуск
echo.

python main.py

pause
"""
    
    launcher_path = os.path.join(os.getcwd(), "ShadowPain.bat")
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(launcher)
    
    print_success(f"  Скрипт создан: {launcher_path}")
    print_info("  Двойной клик для запуска!\n")


def install_python_packages():
    """Установка Python-пакетов"""
    print_info("Установка Python-пакетов...\n")
    
    packages = [
        "requests",
        "PySocks",
        "sherlock-project",
        "wifite2",
    ]
    
    for pkg in packages:
        print_info(f"Установка {pkg}...")
        stdout, stderr, rc = run_command(f'pip install "{pkg}"')
        
        if rc == 0:
            print_success(f"  {pkg} установлен")
        else:
            print_error(f"  {pkg} — ошибка: {stderr[:100]}")
    
    print()
    print_success(" Установка Python-пакетов завершена!")
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Installed Python packages")


def setup_wsl():
    """Настройка WSL для WiFi-инструментов"""
    print_info("Настройка WSL (Windows Subsystem for Linux)\n")
    
    if platform.system() != "Windows":
        print_error(" WSL доступен только на Windows.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    if check_tool("wsl"):
        print_success(" WSL уже установлен.\n")
        print_info("Установка WiFi-инструментов в WSL...\n")
        
        cmd = 'wsl sudo apt update && wsl sudo apt install -y wifite2 aircrack-ng'
        print_info(f"Команда: {cmd}\n")
        
        confirm = input("  Выполнить? (y/n): ").strip().lower()
        if confirm == "y":
            try:
                subprocess.run(cmd, shell=True, check=True)
                print_success(" WiFi-инструменты установлены в WSL!")
            except Exception as e:
                print_error(f" Ошибка: {e}")
        else:
            print_info(" Отменено.")
    else:
        print_warning(" WSL не установлен.\n")
        print_info("Установка WSL (требуется перезагрузка):\n")
        
        cmd = 'wsl --install -d Ubuntu'
        print_info(f"Команда: {cmd}\n")
        
        confirm = input("  Выполнить? (y/n): ").strip().lower()
        if confirm == "y":
            print_warning(" Компьютер будет перезагружен!\n")
            try:
                subprocess.run(cmd, shell=True, check=True)
                print_success(" WSL установлен. Перезагрузите компьютер.")
            except Exception as e:
                print_error(f" Ошибка: {e}")
        else:
            print_info(" Отменено.")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Configured WSL for WiFi tools")


def setup_portable():
    """Настройка portable-режима"""
    clear_screen()
    print_banner()
    print("\n  === Portable-режим ===\n")
    print("  Portable-режим позволяет использовать ShadowPain")
    print("  без установки инструментов на компьютер.\n")
    print("  [1]  Настроить portable-режим")
    print("  [2]  Показать инструкции\n")
    
    choice = input("  >>> Ваш выбор: ").strip()
    
    if choice == "1":
        configure_portable()
    elif choice == "2":
        show_portable_instructions()
    else:
        print_error("Неверный выбор.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)


def configure_portable():
    """Настройка portable-режима"""
    print_info("Настройка portable-режима...\n")
    
    portable_dir = os.path.join(os.getcwd(), "portable")
    os.makedirs(portable_dir, exist_ok=True)
    
    # Создаём portable-конфиг
    config = {
        "portable_mode": True,
        "tools_dir": portable_dir,
        "data_dir": os.path.join(os.getcwd(), "data"),
        "logs_dir": os.path.join(os.getcwd(), "logs"),
    }
    
    import json
    config_path = os.path.join(os.getcwd(), "portable_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print_success(" Portable-режим активирован!")
    print()
    print_info(f" Конфиг: {config_path}")
    print_info(f" Папка инструментов: {portable_dir}")
    print()
    print_warning(" Теперь скачайте portable-версии инструментов:")
    print()
    print("  Hashcat:  https://hashcat.net/hashcat/")
    print("  Wireshark: https://www.wireshark.org/download.html")
    print("  Tor:      https://www.torproject.org/download/")
    print()
    print_info(" Распакуйте в папку portable/")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Configured portable mode")


def show_portable_instructions():
    """Показывает инструкции по portable-использованию"""
    instructions = """
  ╔══════════════════════════════════════════════════════════╗
  ║         Portable-режим: Инструкция                       ║
  ╠══════════════════════════════════════════════════════════╣
  ║                                                          ║
  ║  1.  Hashcat (взлом хешей):                              ║
  ║      → https://hashcat.net/hashcat/                      ║
  ║      → Скачать → Распаковать в portable/                  ║
  ║      → Работает без установки!                            ║
  ║                                                          ║
  ║  2.  Wireshark/tshark (анализ трафика):                  ║
  ║      → https://www.wireshark.org/download.html           ║
  ║      → Скачать Portable Edition                          ║
  ║      → Распаковать в portable/                            ║
  ║                                                          ║
  ║  3.  Tor (анонимность):                                  ║
  ║      → https://www.torproject.org/download/              ║
  ║      → Скачать Tor Browser Bundle                        ║
  ║      → Распаковать в portable/                            ║
  ║                                                          ║
  ║  4.  WiFi-инструменты (Wifite, Aircrack-ng):             ║
  ║      → НЕ работают на Windows!                            ║
  ║      → Вариант A: WSL (см. пункт [3] выше)               ║
  ║      → Вариант B: Linux-флешка (см. ниже)                ║
  ║                                                          ║
  ║  5.  Sherlock (OSINT):                                   ║
  ║      → pip install sherlock-project                       ║
  ║      → Работает сразу!                                    ║
  ║                                                          ║
  ║  6.  Анонимная почта (Mail.tm):                          ║
  ║      → Работает сразу!                                    ║
  ║      → Не требует установки                               ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
    """
    print(instructions)
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Showed portable instructions")


def generate_launcher():
    """Генерация скрипта быстрого запуска"""
    print_info("Генерация скрипта запуска...\n")
    
    launcher = r"""@echo off
chcp 65001 >nul
title ShadowPain Dashboard
cls

echo.
echo   /\ \ \                                 
echo  __     ___     ___\ \ \ \    __  __   __  __   __  __    
echo /'_ `\ /' _ `\  / __`\ \ \ \_ /\ \/\ \ /\ \/\ \ /\ \/\ \   
echo/\ \L\ \/\ \/\ \/\ \L\ \ \__ ,__\ \ \_\ \\ \_\ \\ \_\ \  
echo\ \____ \ \_\ \_\ \____/\/_/\_\_/\/`____ \\/`____ \\/`____ \ 
echo \/___L\ \/_/\/_/\/___/    \/_/   `/___/> \`/___/> \`/___/> \
echo   /\____/                           /\___/   /\___/   /\___/
echo   \_/__/                            \/__/    \/__/    \/__/
echo.
echo   ShadowPain Dashboard — Быстрый запуск
echo.

python main.py

pause
"""
    
    launcher_path = os.path.join(os.getcwd(), "ShadowPain.bat")
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(launcher)
    
    print_success(f" Скрипт создан: {launcher_path}")
    print_info(" Двойной клик для запуска!")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Generated launcher script")


def show_linux_usb_guide():
    """Показывает инструкцию по созданию Linux-флешки для WiFi"""
    guide = """
  ╔══════════════════════════════════════════════════════════╗
  ║  Linux-флешка для WiFi-аудита (портативный Kali)         ║
  ╠══════════════════════════════════════════════════════════╣
  ║                                                          ║
  ║  Для WiFi-аудита на чужом ПК нужен Linux с поддержкой   ║
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
  ║      → Все инструменты уже есть!                          ║
  ║                                                          ║
  ║  5.  ShadowPain на флешке:                               ║
  ║      → Скопировать папку проекта на флешку               ║
  ║      → python main.py                                    ║
  ║      → Всё работает!                                      ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
    """
    print(guide)
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Showed Linux USB guide")
