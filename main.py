"""
ShadowPain Dashboard — Pentest & OSINT Framework
Главный файл запуска
"""

import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import setup_logger
from utils.helpers import clear_screen, print_banner, print_error, print_success, print_info
from config.settings import PROJECT_NAME, VERSION
from modules.osint import run_osint_module
from modules.wifi import run_wifi_module
from modules.hash import run_hash_module
from modules.tor import run_tor_module
from modules.mail import run_email_module
from modules.wireshark import run_wireshark_module
from modules.sqlmap import run_sqlmap_module
from modules.setup import run_setup_module
from modules.portable import run_portable_module
from modules.output_manager import run_output_manager


def main_menu():
    """Главное меню программы"""
    while True:
        clear_screen()
        print_banner()
        print("  [1]  OSINT   — Поиск по никнейму (Sherlock/Quick)")
        print("  [2]  WiFi    — Аудит WiFi (Wifite через WSL)")
        print("  [3]  Hash    — Взлом хешей (Hashcat)")
        print("  [4]  Tor     — Настройка Tor-трафика")
        print("  [5]  Email   — Анонимная почта (Mail.tm)")
        print("  [6]  Network — Анализ трафика (Wireshark)")
        print("  [7]  Setup   — Настройка и установка инструментов")
        print("  [8]  Portable— Portable-режим (на чужом ПК)")
        print("  [9]  SQLMap  — Тестирование SQL-инъекций")
        print("  [10] Output — Управление файлами результатов")
        print("  [0]  Выход")
        print()
        
        try:
            choice = input("  >>> Ваш выбор: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print_success("Выход из ShadowPain. До связи!")
            sys.exit(0)
        
        if choice == "1":
            run_osint_module()
        elif choice == "2":
            run_wifi_module()
        elif choice == "3":
            run_hash_module()
        elif choice == "4":
            run_tor_module()
        elif choice == "5":
            run_email_module()
        elif choice == "6":
            run_wireshark_module()
        elif choice == "7":
            run_setup_module()
        elif choice == "8":
            run_portable_module()
        elif choice == "9":
            run_sqlmap_module()
        elif choice == "10":
            run_output_manager()
        elif choice == "0":
            print_success("Выход из ShadowPain. До связи!")
            sys.exit(0)
        else:
            print_error("Неверный выбор. Попробуйте снова.")
            try:
                input("  [Нажмите Enter для продолжения...]")
            except (EOFError, KeyboardInterrupt):
                print()
                print_success("Выход из ShadowPain. До связи!")
                sys.exit(0)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n")
        print_error("Программа прервана пользователем (Ctrl+C).")
        sys.exit(0)
