"""
WiFi Module — Кроссплатформенный аудит WiFi
Работает на Windows (netsh) и Linux (airodump-ng / aircrack-ng)
"""

import subprocess
import sys
import os
import platform
import re
import shutil
import tempfile

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
        print("  [1]  Сканирование WiFi-сетей")
        print("  [2]  Информация о текущем подключении")
        print("  [3]  Список сохранённых сетей")
        print("  [4]  Запуск aircrack-ng (Linux)")
        print("  [5]  Запуск wifite (Linux)")
        print("  [0]  Назад\n")

        choice = input("  >>> Ваш выбор: ").strip()

        if choice == "1":
            scan_networks()
        elif choice == "2":
            show_connection_info()
        elif choice == "3":
            show_saved_networks()
        elif choice == "4":
            run_aircrack_ng()
        elif choice == "5":
            run_wifite()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            input("  [Enter для продолжения...]")


def _is_windows():
    """Проверка, что работаем на Windows"""
    return platform.system() == "Windows"


def _is_linux():
    """Проверка, что работаем на Linux"""
    return platform.system() == "Linux"


# ========================
#  Windows helpers (netsh)
# ========================

def _run_netsh(args):
    """Выполнить netsh wlan <args> и вернуть stdout"""
    cmd = "netsh wlan " + " ".join(args)
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1
    except Exception as e:
        return "", str(e), -1


def scan_networks_windows():
    """Сканирование WiFi-сетей через netsh (Windows)"""
    print_info("Сканирование WiFi-сетей (netsh)...\n")
    print_warning(" Нажмите Ctrl+C для остановки.\n")

    stdout, stderr, rc = _run_netsh(["show", "networks", "mode=Bssid"])
    if rc != 0:
        print_error(" Не удалось выполнить сканирование.")
        print_info(f" Ошибка: {stderr.strip()}")
        print_info(" Попробуйте запустить от имени администратора.")
        return

    if not stdout.strip():
        print_warning(" Сети не найдены или адаптер отключён.")
        return

    # Парсим вывод netsh
    networks = _parse_netsh_output(stdout)

    if not networks:
        print_warning(" Сети не найдены.")
        return

    print(f"\n  Найдено {len(networks)} сетей:\n")
    print(f"  {'#':<4} {'SSID':<30} {'BSSID':<20} {'Channel':<8} {'Signal':<8} {'Security':<15}")
    print(f"  {'─'*85}\n")

    for idx, net in enumerate(networks, 1):
        print(f"  {idx:<4} {net['ssid']:<30} {net['bssid']:<20} {net['channel']:<8} {net['signal']:<8} {net['security']:<15}")

    print(f"\n  Всего: {len(networks)} сетей")
    print_info("\n  Совет: для глубокого аудита используйте Linux + aircrack-ng")


def show_connection_info_windows():
    """Информация о текущем подключении (Windows)"""
    print_info("Информация о текущем подключении...\n")

    stdout, stderr, rc = _run_netsh(["show", "interfaces"])
    if rc != 0:
        print_error(f" Ошибка: {stderr.strip()}")
        return

    print(stdout)
    print_info("\n  Совет: для глубокого аудита используйте Linux + aircrack-ng")


def show_saved_networks_windows():
    """Список сохранённых WiFi-сетей (Windows)"""
    print_info("Сохранённые WiFi-сети...\n")

    stdout, stderr, rc = _run_netsh(["show", "profiles"])
    if rc != 0:
        print_error(f" Ошибка: {stderr.strip()}")
        return

    profiles = []
    for line in stdout.splitlines():
        if "Все пользовательские профили" in line:
            continue
        m = re.search(r":\s*(.+)$", line)
        if m:
            profiles.append(m.group(1).strip())

    if not profiles:
        print_warning(" Сохранённые сети не найдены.")
        return

    print(f"\n  Сохранено {len(profiles)} сетей:\n")
    for idx, prof in enumerate(profiles, 1):
        print(f"  {idx}. {prof}")

    print_info("\n  Совет: для глубокого аудита используйте Linux + aircrack-ng")


def _parse_netsh_output(output):
    """Парсит вывод netsh show networks"""
    networks = []
    current = {}
    for line in output.splitlines():
        line = line.strip()
        # Ищем SSID
        m = re.match(r"^\s*(.+?)\s{2,}", line)
        if m and "SSID" not in line and ":" not in line:
            current["ssid"] = line.strip()
        # Ищем BSSID
        m = re.match(r"BSSID\s+([0-9A-Fa-f:]+)", line)
        if m:
            current["bssid"] = m.group(1)
        # Ищем канал
        m = re.match(r"Channel\s+(\d+)", line)
        if m:
            current["channel"] = m.group(1)
        # Ищем сигнал
        m = re.match(r"Signal\s+(\d+)%", line)
        if m:
            current["signal"] = m.group(1) + "%"
        # Ищем тип безопасности
        m = re.match(r"Authentication\s+\((.+)\)", line)
        if m:
            current["security"] = m.group(1)
        # Новая сеть начинается с пустой строки или нового SSID
        if not line or (line and "SSID" in line and ":" not in line):
            if current.get("ssid"):
                networks.append(current)
            current = {}
    if current.get("ssid"):
        networks.append(current)
    return networks


# ========================
#  Linux helpers (aircrack-ng)
# ========================

def _check_linux_tool(name):
    """Проверка наличия утилиты в Linux"""
    return shutil.which(name) is not None


def _run_linux(cmd, sudo=False):
    """Выполнить команду на Linux"""
    if sudo:
        cmd = "sudo " + cmd
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1
    except Exception as e:
        return "", str(e), -1


def scan_networks_linux():
    """Сканирование WiFi-сетей через airodump-ng (Linux)"""
    print_info("Сканирование WiFi-сетей...\n")

    if not _check_linux_tool("airodump-ng"):
        print_error(" airodump-ng не установлен.")
        print_info(" Установите: sudo apt install -y aircrack-ng")
        return

    # Проверяем, есть ли monitor-интерфейс
    stdout, _, _ = _run_linux("airmon-ng")
    monitor_if = None
    for line in stdout.splitlines():
        if "mon" in line and "wlan" in line.lower():
            parts = line.split()
            if parts:
                monitor_if = parts[0]
                break

    # Если нет monitor-интерфейса, пробуем включить
    if not monitor_if:
        print_warning(" Monitor-интерфейс не найден. Пытаемся включить...")
        # Ищем WiFi-интерфейс
        stdout2, _, _ = _run_linux("ip link show | grep -E 'wlan|wl'")
        if stdout2.strip():
            iface = stdout2.strip().split(":")[0].strip()
            print_info(f"  Включаем monitor mode на {iface}...")
            _run_linux(f"airmon-ng start {iface}")
            monitor_if = f"{iface}mon"
        else:
            # Пробуем wlan0
            _run_linux("airmon-ng start wlan0")
            monitor_if = "wlan0mon"

    if not monitor_if:
        print_error(" Не удалось найти WiFi-интерфейс.")
        return

    print_info(f"  Monitor-интерфейс: {monitor_if}\n")
    print_warning("  Нажмите Ctrl+C для остановки.\n")

    try:
        result = subprocess.run(
            f"sudo airodump-ng {monitor_if}",
            shell=True,
            check=False,
        )
    except KeyboardInterrupt:
        print_warning("\n  Сканирование остановлено.")
    except Exception as e:
        print_error(f"  Ошибка: {e}")

    print_info("\n  Совет: для автоматизации используйте wifite")


def run_aircrack_ng():
    """Запуск aircrack-ng (только Linux)"""
    if not _is_linux():
        print_warning(" aircrack-ng работает только на Linux.")
        print_info(" Для Windows используйте netsh (пункты 1-3).\n")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return

    print_info("Запуск aircrack-ng...\n")

    if not _check_linux_tool("aircrack-ng"):
        print_error(" aircrack-ng не установлен.")
        print_info(" Установите: sudo apt install -y aircrack-ng")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return

    print_warning(" aircrack-ng запустится в интерактивном режиме.")
    print_info(" Используйте его для аудита WEP/WPA-сетей.\n")

    try:
        subprocess.run("aircrack-ng", shell=True, check=True)
        print_success("aircrack-ng завершён.")
    except KeyboardInterrupt:
        print_warning(" aircrack-ng остановлен пользователем.")
    except Exception as e:
        print_error(f" Ошибка: {e}")

    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)


def run_wifite():
    """Запуск wifite (только Linux)"""
    if not _is_linux():
        print_warning(" wifite работает только на Linux.")
        print_info(" Для Windows используйте netsh (пункты 1-3).\n")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return

    print_warning(" ⚠  ВНИМАНИЕ: Используйте только на собственных сетях!")
    print_info("Запуск wifite...\n")

    if not _check_linux_tool("wifite"):
        print_error(" wifite не установлен.")
        print_info(" Установите: sudo apt install -y wifite")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return

    try:
        subprocess.run("wifite", shell=True, check=True)
        print_success("wifite завершён.")
    except KeyboardInterrupt:
        print_warning(" wifite остановлен пользователем.")
    except Exception as e:
        print_error(f" Ошибка: {e}")

    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)


# ========================
#  Кроссплатформенные обёртки
# ========================

def scan_networks():
    """Кроссплатформенное сканирование WiFi-сетей"""
    if _is_windows():
        scan_networks_windows()
    elif _is_linux():
        scan_networks_linux()
    else:
        print_error(" Неподдерживаемая платформа.")
        print_info(" Поддерживаются: Windows и Linux.")
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)


def show_connection_info():
    """Кроссплатформенная информация о подключении"""
    if _is_windows():
        show_connection_info_windows()
    elif _is_linux():
        print_info("Запрос информации о подключении...\n")
        stdout, _, rc = _run_linux("iwconfig 2>/dev/null || ip link show | grep -E 'wlan|wl'")
        if rc == 0 and stdout.strip():
            print(stdout)
        else:
            print_warning(" Не удалось получить информацию о подключении.")
            print_info(" Попробуйте: sudo iwconfig")
    else:
        print_error(" Неподдерживаемая платформа.")
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)


def show_saved_networks():
    """Кроссплатформенный список сохранённых сетей"""
    if _is_windows():
        show_saved_networks_windows()
    elif _is_linux():
        print_info("Сохранённые WiFi-сети (NetManager/NetworkManager)...\n")
        stdout, _, rc = _run_linux("nmcli device wifi list 2>/dev/null")
        if rc == 0 and stdout.strip():
            print("\n  Доступные сети:\n")
            print(stdout)
        else:
            print_warning(" Не удалось получить список сетей.")
            print_info(" Убедитесь, что NetworkManager запущен.")
    else:
        print_error(" Неподдерживаемая платформа.")
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)


# ========================
#  Старая совместимость
# ========================

# Эти функции остаются для обратной совместимости, но вызывают новый код
run_wifite_compat = run_wifite
scan_networks_compat = scan_networks
