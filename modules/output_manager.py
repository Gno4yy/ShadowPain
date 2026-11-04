"""
Output Manager Module — Управление файлами результатов
Просмотр, удаление файлов из папки output/
"""

import os
import sys
from datetime import datetime

# Добавляем корень проекта в путь при запуске напрямую
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from utils.helpers import (
    clear_screen, print_banner, print_success, print_error,
    print_info, print_warning, safe_input
)
from utils.logger import setup_logger

logger = setup_logger()

OUTPUT_DIR = os.path.join(_project_root, "output")


def run_output_manager():
    """Менеджер файлов результатов"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === Output: Управление файлами результатов ===\n")
        
        files = get_output_files()
        
        if not files:
            print_info(" Папка output/ пуста.\n")
        else:
            print(f"  Файлов: {len(files)}\n")
            print("  \033[93m  №  |  Имя файла                    |  Размер  |  Дата\033[0m")
            print("  " + "─" * 70)
            for i, f in enumerate(files, 1):
                size_str = format_size(f["size"])
                date_str = f["date"]
                name = f["name"][:25]
                print(f"  \033[94m  {i:2d}  |  {name:<25s} |  {size_str:>6s}  |  {date_str}\033[0m")
            print()
        
        print("  [1]  Очистить все файлы")
        print("  [2]  Удалить выбранный файл")
        print("  [3]  Удалить по паттерну")
        print("  [4]  Открыть папку output")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            clear_all_files()
        elif choice == "2":
            delete_single_file()
        elif choice == "3":
            delete_by_pattern()
        elif choice == "4":
            open_output_folder()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            if safe_input("  [Enter для продолжения...]") is None:
                sys.exit(0)


def get_output_files():
    """Получить список файлов в output/"""
    if not os.path.exists(OUTPUT_DIR):
        return []
    
    files = []
    for name in os.listdir(OUTPUT_DIR):
        filepath = os.path.join(OUTPUT_DIR, name)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append({
                "name": name,
                "path": filepath,
                "size": stat.st_size,
                "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    
    # Сортировка по дате (новые первые)
    files.sort(key=lambda x: x["date"], reverse=True)
    return files


def format_size(size_bytes):
    """Форматирование размера файла"""
    for unit in ["Б", "КБ", "МБ", "ГБ"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} ТБ"


def clear_all_files():
    """Удаление всех файлов из output/"""
    files = get_output_files()
    
    if not files:
        print_info(" Папка output/ уже пуста.\n")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    print_warning(f" Удалить ВСЕ {len(files)} файлов из output/?")
    confirm = input("  Введите 'удалить' для подтверждения: ").strip()
    
    if confirm.lower() != "удалить":
        print_info(" Отменено.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    deleted = 0
    for f in files:
        try:
            os.remove(f["path"])
            deleted += 1
        except Exception as e:
            print_error(f" Ошибка удаления {f['name']}: {e}")
    
    print_success(f" Удалено файлов: {deleted}/{len(files)}")
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Cleared all output files: {deleted} deleted")


def delete_single_file():
    """Удаление одного файла по номеру"""
    files = get_output_files()
    
    if not files:
        print_info(" Папка output/ пуста.\n")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    try:
        num = int(input("  Номер файла: ").strip()) - 1
        if 0 <= num < len(files):
            f = files[num]
            print(f"\n  Удалить: {f['name']} ({format_size(f['size'])})")
            confirm = input("  [y/n]: ").strip().lower()
            
            if confirm == "y":
                os.remove(f["path"])
                print_success(f" Файл удалён: {f['name']}")
            else:
                print_info(" Отменено.")
        else:
            print_error(" Неверный номер.")
    except ValueError:
        print_error(" Введите число.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Deleted single file")


def delete_by_pattern():
    """Удаление файлов по паттерну"""
    pattern = input("  Паттерн (напр. 'osint_', '*.json'): ").strip()
    
    if not pattern:
        print_error(" Паттерн не указан!")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    import fnmatch
    
    files = get_output_files()
    matched = [f for f in files if fnmatch.fnmatch(f["name"], pattern)]
    
    if not matched:
        print_info(f" Файлов по паттерну '{pattern}' не найдено.\n")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    print(f"\n  Найдено {len(matched)} файлов:\n")
    for i, f in enumerate(matched, 1):
        print(f"    [{i}] {f['name']} ({format_size(f['size'])})")
    
    confirm = input(f"\n  Удалить {len(matched)} файлов? (y/n): ").strip().lower()
    
    if confirm == "y":
        deleted = 0
        for f in matched:
            try:
                os.remove(f["path"])
                deleted += 1
            except Exception as e:
                print_error(f" Ошибка удаления {f['name']}: {e}")
        
        print_success(f" Удалено: {deleted}/{len(matched)}")
    else:
        print_info(" Отменено.")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Deleted files by pattern: {pattern}, {len(matched)} matched")


def open_output_folder():
    """Открытие папки output в проводнике"""
    import subprocess
    
    if not os.path.exists(OUTPUT_DIR):
        print_info(" Папка output/ не существует.\n")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    try:
        if sys.platform == "win32":
            os.startfile(OUTPUT_DIR)
        elif sys.platform == "darwin":
            subprocess.run(["open", OUTPUT_DIR])
        else:
            subprocess.run(["xdg-open", OUTPUT_DIR])
        print_success(" Папка открыта в проводнике.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
        print_info(f" Путь: {OUTPUT_DIR}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Opened output folder")
