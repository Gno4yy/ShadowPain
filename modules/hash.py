"""
Hash Module — Работа с хешами через Hashcat
"""

import subprocess
import sys
import os

# Добавляем корень проекта в путь при запуске напрямую
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from utils.helpers import (
    clear_screen, print_banner, print_success, print_error,
    print_info, print_warning, run_command, check_tool, save_output,
    safe_input
)
from utils.logger import setup_logger

logger = setup_logger()


def run_hash_module():
    """Модуль работы с хешами (Hashcat)"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === Hash: Взлом/проверка хешей (Hashcat) ===\n")
        print("  [1]  Straight attack (словарь)")
        print("  [2]  Brute-force (маска)")
        print("  [3]  Определение типа хеша")
        print("  [4]  Список режимов хеширования")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            hash_attack_dict()
        elif choice == "2":
            hash_attack_brute()
        elif choice == "3":
            identify_hash()
        elif choice == "4":
            show_hash_modes()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            input("  [Enter для продолжения...]")


def hash_attack_dict():
    """Straight attack через словарь"""
    print_info("Straight Attack (словарь)")
    print()
    
    if not check_tool("hashcat"):
        print_error("Hashcat не найден! Скачайте с https://hashcat.net/hashcat/")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    hash_input = input("  Введите хеш: ").strip()
    dict_path = input("  Путь к словарю (wordlist.txt): ").strip() or "wordlist.txt"
    
    if not os.path.exists(dict_path):
        print_error(f"Словарь не найден: {dict_path}")
        print_info("Скачайте rockyou.txt: https://github.com/brannondorsey/naive-hashcat/releases")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Определяем режим хеша автоматически
    hash_mode = auto_detect_hash(hash_input)
    
    cmd = f'hashcat -m {hash_mode} -a 0 {hash_input} "{dict_path}"'
    
    print_info(f"Режим хеша: {hash_mode}")
    print_info(f"Команда: {cmd}")
    print_info("Запуск... (Ctrl+C для остановки)\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print_success("Атака завершена!")
    except KeyboardInterrupt:
        print_warning("Атака остановлена.")
    except Exception as e:
        print_error(f"Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Hashcat dictionary attack: mode={hash_mode}")


def hash_attack_brute():
    """Brute-force атака через маску"""
    print_info("Brute-Force Attack (маска)")
    print()
    
    if not check_tool("hashcat"):
        print_error("Hashcat не найден!")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    hash_input = input("  Введите хеш: ").strip()
    mask = input("  Маска (?d=цифры, ?l=буквы, ?a=все): ").strip() or "?d?d?d?d"
    
    hash_mode = auto_detect_hash(hash_input)
    
    cmd = f'hashcat -m {hash_mode} -a 3 {hash_input} "{mask}"'
    
    print_info(f"Режим хеша: {hash_mode}")
    print_info(f"Маска: {mask}")
    print_info("Запуск...\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print_success("Атака завершена!")
    except KeyboardInterrupt:
        print_warning("Атака остановлена.")
    except Exception as e:
        print_error(f"Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Hashcat brute-force attack: mode={hash_mode}, mask={mask}")


def identify_hash():
    """Попытка определить тип хеша"""
    hash_input = input("  Введите хеш для анализа: ").strip()
    
    if not hash_input:
        print_error("Хеш не введён!")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Простой анализ по длине и символу
    length = len(hash_input)
    hash_lower = hash_input.lower()
    
    print(f"\n  Анализ хеша: {hash_input[:30]}{'...' if len(hash_input) > 30 else ''}")
    print(f"  Длина: {length}\n")
    
    hash_types = {
        32: ["MD5 (mode 0)", "MySQL SHA1 (mode 800)"],
        40: ["SHA-1 (mode 100)"],
        64: ["SHA-256 (mode 1400)", "SHA-512/256 (mode 1710)"],
        128: ["SHA-512 (mode 1700)"],
    }
    
    if length in hash_types:
        print_success(" Возможные типы:")
        for ht in hash_types[length]:
            print(f"    → {ht}")
    else:
        print_warning(" Не удалось определить тип по длине.")
        print_info(" Используйте hashcat -h | grep mode для списка режимов.")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)


def auto_detect_hash(hash_input):
    """Автоматическое определение режима хеша"""
    length = len(hash_input)
    hash_lower = hash_input.lower()
    
    # Проверяем на Base64
    if hash_lower.endswith('$'):
        parts = hash_lower.split('$')
        if parts[1].isdigit():
            return parts[1]
    
    # По длине
    mode_map = {
        32: "0",     # MD5
        40: "100",   # SHA-1
        64: "1400",  # SHA-256
        128: "1700", # SHA-512
    }
    
    return mode_map.get(length, "0")


def show_hash_modes():
    """Показ популярных режимов хеширования"""
    modes = """
  Популярные режимы Hashcat:
  ─────────────────────────────────
   Mode  | Хеш
  ─────────────────────────────────
      0  | MD5
    100  | SHA-1
    1000 | NTLM
   1400  | SHA-256
   1700  | SHA-512
   1800  | SHA-3_512
    500  | MD5(Unix)
    1000 | NTLM
    3000 | LM
   4000  | sha1crypt / Jooma
   5700  | bcrypt $2*$
   900  | MD5($pass.$salt)
   ─────────────────────────────────
   Полный список: hashcat -h | grep mode
     """
    print(modes)
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Displayed hashcat modes list")
