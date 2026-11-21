import os
import sys
import subprocess
import platform

# Корень проекта — для абсолютных путей
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Загружаем баннер из файла или используем дефолтный
_DEFAULT_BANNER = r"""
                                      
  __     ___     ___\ \ \ \    __  __   __  __   __  __    
 /'_ `\ /' _ `\  / __`\ \ \ \_ /\ \/\ \ /\ \/\ \ /\ \/\ \   
/\ \L\ \/\ \/\ \/\ \L\ \ \__ ,__\ \ \_\ \\ \ \_\ \\ \ \_\ \  
\ \____ \ \_\ \_\ \____/\/_/\_\_/\/`____ \\/`____ \\/`____ \ 
 \/___L\ \/_/\/_/\/___/    \/_/   `/___/> \`/___/> \`/___/> \
    /\____/                           /\___/   /\___/   /\___/
    \_/__/                            \/__/    \/__/    \/__/
    
"""

def _load_banner():
    """Загружает баннер из файла или возвращает дефолтный"""
    from config.settings import BANNER_FILE
    banner_path = os.path.join(PROJECT_ROOT, BANNER_FILE)
    if os.path.exists(banner_path):
        try:
            with open(banner_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return "\n" + content + "\n"
        except Exception:
            pass
    return _DEFAULT_BANNER


def clear_screen():
    """Очистка экрана"""
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def print_banner():
    """Вывод ASCII-баннера"""
    print(_load_banner())


def print_success(msg):
    print(f"\033[92m[+] {msg}\033[0m")


def print_error(msg):
    print(f"\033[91m[-] {msg}\033[0m")


def print_info(msg):
    print(f"\033[94m[i] {msg}\033[0m")


def print_warning(msg):
    print(f"\033[93m[!] {msg}\033[0m")


def run_command(cmd, capture=True):
    """Запуск командной строки"""
    try:
        if capture:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=3600
            )
            return result.stdout, result.stderr, result.returncode
        else:
            subprocess.run(cmd, shell=True, check=True)
            return "", "", 0
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1
    except Exception as e:
        return "", str(e), -1


def check_tool(name):
    """Проверка наличия утилиты в системе"""
    import shutil
    
    # 1. Стандартная проверка в PATH
    if shutil.which(name) is not None:
        return True
    
    # 2. Проверка в portable/
    portable_exe = os.path.join(PROJECT_ROOT, "portable", name)
    if os.path.isfile(portable_exe):
        return True
    portable_exe_py = os.path.join(PROJECT_ROOT, "portable", name, f"{name}.py")
    if os.path.isfile(portable_exe_py):
        return True
    # Windows portable
    portable_exe_win = os.path.join(PROJECT_ROOT, "portable", name, f"{name}.exe")
    if os.path.isfile(portable_exe_win):
        return True
    
    # 3. Проверка в Python Scripts/Scripts
    python_dir = os.path.dirname(sys.executable)
    for subdir in ["Scripts", "bin"]:
        script_path = os.path.join(python_dir, subdir, name)
        if os.path.isfile(script_path):
            return True
        # Windows: .exe
        if os.path.isfile(f"{script_path}.exe"):
            return True
    
    # 4. Проверка в site-packages
    import glob
    site_packages_pattern = os.path.join(python_dir, "lib", "python*", "site-packages")
    matched_sp = glob.glob(site_packages_pattern)
    if not matched_sp:
        alt_sp = os.path.join(python_dir, "Lib", "site-packages")
        matched_sp = [alt_sp] if os.path.isdir(alt_sp) else []
    for sp_dir in matched_sp:
        for root, dirs, files in os.walk(sp_dir):
            if name in files or f"{name}.exe" in files:
                return True
    
    return False


def get_portable_tool(name):
    """Получить путь к portable-версии утилиты или None"""
    portable_dir = os.path.join(PROJECT_ROOT, "portable")
    
    # 1. Прямой файл в portable/
    direct = os.path.join(portable_dir, name)
    if os.path.isfile(direct):
        return direct
    
    # 2. Файл в portable/name/name.py или portable/name/name.exe
    subdir = os.path.join(portable_dir, name)
    if os.path.isdir(subdir):
        py_file = os.path.join(subdir, f"{name}.py")
        exe_file = os.path.join(subdir, f"{name}.exe")
        if os.path.isfile(py_file):
            return py_file
        if os.path.isfile(exe_file):
            return exe_file
        # Ищем любой исполняемый файл
        for root, dirs, files in os.walk(subdir):
            for f in files:
                if f.endswith(('.exe', '.py', '.sh')):
                    return os.path.join(root, f)
    
    return None


def save_output(filename, content):
    """Сохранение результата в файл"""
    output_dir = os.path.join(PROJECT_ROOT, "output")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def safe_input(prompt=""):
    """Безопасный ввод — обрабатывает EOFError и KeyboardInterrupt"""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def change_banner():
    """Изменение баннера ShadowPain"""
    from config.settings import BANNER_FILE
    
    banner_path = os.path.join(PROJECT_ROOT, BANNER_FILE)
    
    # Создаём папку data если нет
    os.makedirs(os.path.dirname(banner_path), exist_ok=True)
    
    print_info("Доступные варианты:\n")
    print("  [1]  Ввести свой баннер (ввод с клавиатуры)")
    print("  [2]  Загрузить из файла")
    print("  [3]  Сбросить на дефолтный")
    print("  [0]  Назад\n")
    
    choice = input("  >>> Ваш выбор: ").strip()
    
    if choice == "0":
        return
    
    if choice == "1":
        print_info("Введите баннер (завершите пустой строкой):\n")
        lines = []
        while True:
            try:
                line = input()
                if line == "" and lines:
                    break
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                break
        
        banner_text = "\n".join(lines)
        if banner_text.strip():
            with open(banner_path, "w", encoding="utf-8") as f:
                f.write(banner_text + "\n")
            print_success("  Баннер сохранён!")
        else:
            print_warning("  Баннер пустой — не сохранён.")
    
    elif choice == "2":
        filepath = input("  Путь к файлу с баннером: ").strip()
        if not filepath:
            print_error("  Путь не указан!")
            return
        
        if not os.path.exists(filepath):
            print_error(f"  Файл не найден: {filepath}")
            return
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                print_warning("  Файл пустой.")
                return
            
            with open(banner_path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            print_success("  Баннер загружен из файла!")
        except Exception as e:
            print_error(f"  Ошибка чтения файла: {e}")
    
    elif choice == "3":
        if os.path.exists(banner_path):
            os.remove(banner_path)
            print_success("  Баннер сброшен на дефолтный!")
        else:
            print_info("  Баннер уже дефолтный.")
    
    else:
        print_error("  Неверный выбор.")
