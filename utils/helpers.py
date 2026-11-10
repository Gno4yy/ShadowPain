import os
import sys
import subprocess
import platform

# Корень проекта — для абсолютных путей
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def clear_screen():
    """Очистка экрана"""
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def print_banner():
    """Вывод ASCII-баннера"""
    banner = r"""
                                     
  __     ___     ___\ \ \ \    __  __   __  __   __  __    
 /'_ `\ /' _ `\  / __`\ \ \ \_ /\ \/\ \ /\ \/\ \ /\ \/\ \   
/\ \L\ \/\ \/\ \/\ \L\ \ \__ ,__\ \ \_\ \\ \ \_\ \\ \ \_\ \  
\ \____ \ \_\ \_\ \____/\/_/\_\_/\/`____ \\/`____ \\/`____ \ 
 \/___L\ \/_/\/_/\/___/    \/_/   `/___/> \`/___/> \`/___/> \
   /\____/                           /\___/   /\___/   /\___/
   \_/__/                            \/__/    \/__/    \/__/
   
"""
    print(banner)


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
    
    # 2. Проверка в Python Scripts/Scripts
    python_dir = os.path.dirname(sys.executable)
    for subdir in ["Scripts", "bin"]:
        script_path = os.path.join(python_dir, subdir, name)
        if os.path.isfile(script_path):
            return True
        # Windows: .exe
        if os.path.isfile(f"{script_path}.exe"):
            return True
    
    # 3. Проверка в site-packages
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
