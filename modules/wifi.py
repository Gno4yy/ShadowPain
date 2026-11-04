"""
WiFi Module — Аудит WiFi-сетей через Wifite
Поддержка WSL и Linux-флешки для использования на чужом ПК
"""

import subprocess
import sys
import os
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


def run_wifi_module():
    """Модуль WiFi-аудита"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === WiFi: Аудит беспроводных сетей ===\n")
        print("  [1]  Запустить Wifite (через WSL)")
        print("  [2]  Сканирование сетей (airodump-ng через WSL)")
        print("  [3]  Проверка WSL-окружения")
        print("  [4]  Инструкция по Linux-флешке")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            run_wifite()
        elif choice == "2":
            scan_networks()
        elif choice == "3":
            check_wsl_env()
        elif choice == "4":
            show_usb_guide()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            input("  [Enter для продолжения...]")


def run_wifite():
    """Запуск Wifite через WSL"""
    print_warning("⚠  ВНИМАНИЕ: Используйте только на собственных сетях!")
    print_info("Запуск Wifite через WSL...\n")
    
    if platform.system() != "Windows":
        print_error(" Этот модуль предназначен для Windows + WSL.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Проверяем WSL
    if not check_tool("wsl"):
        print_error(" WSL не установлен!")
        print()
        print_info("Установка WSL:")
        print("  1. PowerShell от админа:")
        print("     wsl --install")
        print("  2. Перезагрузить компьютер")
        print("  3. Установить WiFi-инструменты:")
        print("     wsl sudo apt update")
        print("     wsl sudo apt install -y wifite2 aircrack-ng")
        print()
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Проверяем wifite в WSL
    stdout, stderr, rc = run_command('wsl which wifite2 || wsl which wifite')
    if rc != 0:
        print_warning(" Wifite не найден в WSL.\n")
        print_info("Установка WiFi-инструментов в WSL:\n")
        
        confirm = input("  Установить? (y/n): ").strip().lower()
        if confirm == "y":
            print_info("Обновление пакетов...")
            run_command('wsl sudo apt update')
            print_info("Установка wifite2 и aircrack-ng...")
            stdout, stderr, rc = run_command('wsl sudo apt install -y wifite2 aircrack-ng')
            if rc == 0:
                print_success(" WiFi-инструменты установлены!")
            else:
                print_error(" Ошибка установки.")
        else:
            print_info(" Отменено.")
        
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    print_info("Запуск Wifite через WSL...\n")
    print_warning(" WiFi-карта должна поддерживать monitor mode!")
    print_info("Для WiFi-аудита нужен адаптер с поддержкой monitor mode.\n")
    
    try:
        subprocess.run('wsl wifite', shell=True, check=True)
        print_success("Wifite завершён.")
    except KeyboardInterrupt:
        print_warning("Wifite остановлен пользователем.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Wifite audit executed via WSL")


def scan_networks():
    """Сканирование WiFi-сетей через airodump-ng в WSL"""
    print_info("Сканирование WiFi-сетей через WSL...\n")
    
    if platform.system() != "Windows":
        print_error(" Этот модуль предназначен для Windows + WSL.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    if not check_tool("wsl"):
        print_error(" WSL не установлен!")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Проверяем airodump-ng
    stdout, _, rc = run_command('wsl which airodump-ng')
    if rc != 0:
        print_error(" airodump-ng не найден в WSL.")
        print_info("Установите: wsl sudo apt install -y aircrack-ng")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    print_info("Сканирование запущено...\n")
    print_warning(" Нажмите Ctrl+C для остановки.\n")
    
    try:
        subprocess.run('wsl airodump-ng wlan0mon', shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Сканирование остановлено.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
        print_info(" Проверьте имя интерфейса: wsl airmon-ng")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("WiFi scan executed via WSL")


def check_wsl_env():
    """Проверка WSL-окружения и WiFi-инструментов"""
    clear_screen()
    print_banner()
    print("\n  === Проверка WSL-окружения ===\n")
    
    if platform.system() != "Windows":
        print_error(" WSL доступен только на Windows.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Проверяем WSL
    if not check_tool("wsl"):
        print_error(" WSL не установлен!")
        print()
        print_info("Установка: wsl --install (PowerShell от админа)")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    print_success(" WSL установлен\n")
    
    # Проверяем дистрибутив
    stdout, _, _ = run_command("wsl --list --verbose")
    if stdout.strip():
        print_info("Установленные дистрибутивы:\n")
        print(stdout)
    
    # Проверяем WiFi-инструменты
    tools = ["wifite", "wifite2", "airodump-ng", "aircrack-ng", "airmon-ng"]
    
    print("\n  WiFi-инструменты в WSL:")
    print("  ─────────────────────────────────────────")
    
    for tool in tools:
        stdout, _, rc = run_command(f'wsl which {tool}')
        if rc == 0:
            print(f"  \033[92m[✓]\033[0m  {tool:20s} — установлен")
        else:
            print(f"  \033[91m[✗]\033[0m  {tool:20s} — НЕ УСТАНОВЛЕН")
    
    # Проверяем WiFi-адаптер
    print("\n  WiFi-адаптер:")
    stdout, _, _ = run_command("wsl airmon-ng")
    if stdout.strip():
        print_info("\n Доступные интерфейсы:\n")
        print(stdout)
    else:
        print_warning(" Не удалось получить список WiFi-интерфейсов.")
        print_info(" Убедитесь, что WiFi-адаптер подключён и поддерживает monitor mode.")
    
    if safe_input("\n  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Checked WSL environment")


def show_usb_guide():
    """Показывает инструкцию по созданию Linux-флешки"""
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
  ║  6.  Альтернатива — VirtualBox + Kali VM:                ║
  ║      → Скачать VirtualBox: https://virtualbox.org        ║
  ║      → Скачать Kali VM: https://www.kali.org/get-kali/   ║
  ║      → Подключить WiFi-адаптер к VM                     ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
    """
    print(guide)
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Showed Linux USB guide")
