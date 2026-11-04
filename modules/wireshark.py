"""
Wireshark Module — Анализ сетевого трафика через tshark
"""

import subprocess
import sys
import os
import time

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


def run_wireshark_module():
    """Модуль Wireshark / tshark — анализ сетевого трафика"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === Wireshark: Анализ сетевого трафика (tshark) ===\n")
        print("  [1]  Показать доступные интерфейсы")
        print("  [2]  Захват пакетов (live capture)")
        print("  [3]  Анализ сохранённого файла (.pcap)")
        print("  [4]  Фильтрация трафика")
        print("  [5]  Мониторинг в реальном времени")
        print("  [6]  Перехват DNS-запросов")
        print("  [7]  Перехват HTTP-трафика")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            list_interfaces()
        elif choice == "2":
            start_capture()
        elif choice == "3":
            analyze_pcap()
        elif choice == "4":
            traffic_filter()
        elif choice == "5":
            live_monitor()
        elif choice == "6":
            capture_dns()
        elif choice == "7":
            capture_http()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            input("  [Enter для продолжения...]")


def get_tshark():
    """Получить путь к tshark"""
    if check_tool("tshark"):
        return "tshark"
    
    # Стандартные пути установки Wireshark на Windows
    paths = [
        r"C:\Program Files\Wireshark\tshark.exe",
        r"C:\Program Files (x86)\Wireshark\tshark.exe",
    ]
    
    for p in paths:
        if os.path.exists(p):
            return p
    
    return None


def check_tshark():
    """Проверка наличия tshark и вывод понятной ошибки"""
    tshark = get_tshark()
    if not tshark:
        print_error("tshark не найден!")
        print()
        print_info("Wireshark не установлен.")
        print_info("Скачайте с: https://www.wireshark.org/download.html")
        print_info("После установки убедитесь, что Npcap установлен.")
        print()
        print_warning("Без администраторских прав захват может не работать.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return False
    return True


def list_interfaces():
    """Показать все сетевые интерфейсы"""
    print_info("Загрузка списка интерфейсов...")
    
    if not check_tshark():
        return
    
    cmd = "tshark -D"
    stdout, stderr, rc = run_command(cmd)
    
    if rc == 0 and stdout.strip():
        print_success("\n Доступные интерфейсы:\n")
        print(stdout)
    else:
        print_error("Не удалось получить список интерфейсов.")
        print_error(stderr)
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Listed network interfaces")


def start_capture():
    """Захват пакетов в реальном времени"""
    print_info("Захват пакетов...\n")
    
    if not check_tshark():
        return
    
    # Показываем интерфейсы
    cmd = "tshark -D"
    stdout, _, _ = run_command(cmd)
    
    if not stdout.strip():
        print_error("Нет доступных интерфейсов для захвата.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    print(" Доступные интерфейсы:")
    print(stdout)
    
    iface_num = input("  Номер интерфейса (или 'all' для всех): ").strip()
    
    if iface_num.lower() == "all":
        iface = "-i any"
    else:
        iface = f"-i {iface_num}"
    
    duration = input("  Длительность захвата в секундах (0 = бесконечно): ").strip() or "0"
    output_file = input("  Сохранить в файл (.pcap) (пусто = не сохранять): ").strip()
    
    if output_file and not output_file.endswith(".pcap"):
        output_file += ".pcap"
    
    cmd = f'tshark {iface}'
    
    if duration and duration != "0":
        cmd += f" -a duration:{duration}"
    
    if output_file:
        cmd += f' -w "{output_file}"'
    
    cmd += " -V"  # verbose — подробный вывод
    
    print()
    print_warning(" Захват запущен. Нажмите Ctrl+C для остановки.")
    print_info(f" Файл: {output_file or 'не сохранён'}\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Захват остановлен.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if output_file:
        filepath = save_output(os.path.basename(output_file), f"Захват завершён: {output_file}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Capture started on interface: {iface_num}")


def analyze_pcap():
    """Анализ сохранённого .pcap файла"""
    print_info("Анализ .pcap файла\n")
    
    pcap_path = input("  Путь к файлу .pcap: ").strip().strip('"')
    
    if not os.path.exists(pcap_path):
        print_error(f" Файл не найден: {pcap_path}")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    print()
    print("  [1]  Общая статистика")
    print("  [2]  Список IP-адресов")
    print("  [3]  Список MAC-адресов")
    print("  [4]  Протоколы")
    print("  [5]  Топ-5 общающихся хостов")
    print("  [6]  Полный вывод")
    print("  [0]  Назад\n")
    
    choice = input("  >>> Ваш выбор: ").strip()
    
    if choice == "0":
        return
    elif choice == "1":
        cmd = f'tshark -r "{pcap_path}" -q -z io,stat,1'
        stdout, stderr, rc = run_command(cmd)
        if rc == 0:
            print_success("\n Статистика захвата:\n")
            print(stdout)
        else:
            print_error(stderr)
    
    elif choice == "2":
        cmd = f'tshark -r "{pcap_path}" -T fields -e ip.src -e ip.dst 2>/dev/null'
        stdout, _, _ = run_command(cmd)
        if stdout.strip():
            print_success("\n IP-адреса:\n")
            print(stdout)
        else:
            print_info(" IP-данные не найдены.")
    
    elif choice == "3":
        cmd = f'tshark -r "{pcap_path}" -T fields -e eth.src -e eth.dst 2>/dev/null'
        stdout, _, _ = run_command(cmd)
        if stdout.strip():
            print_success("\n MAC-адреса:\n")
            print(stdout)
        else:
            print_info(" MAC-данные не найдены.")
    
    elif choice == "4":
        cmd = f'tshark -r "{pcap_path}" -q -z io,phs'
        stdout, stderr, rc = run_command(cmd)
        if rc == 0:
            print_success("\n Протоколы:\n")
            print(stdout)
        else:
            print_error(stderr)
    
    elif choice == "5":
        cmd = f'tshark -r "{pcap_path}" -T fields -e ip.src 2>/dev/null | sort | uniq -c | sort -rn | head -5'
        stdout, _, _ = run_command(cmd)
        if stdout.strip():
            print_success("\n Топ-5 хостов:\n")
            print(stdout)
    
    elif choice == "6":
        print_info("Полный вывод (Ctrl+C для выхода):\n")
        try:
            subprocess.run(f'tshark -r "{pcap_path}"', shell=True, check=True)
        except KeyboardInterrupt:
            pass
    else:
        print_error("Неверный выбор.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Analyzed pcap file: {pcap_path}")


def traffic_filter():
    """Фильтрация трафика"""
    print_info("Фильтрация трафика\n")
    
    pcap_path = input("  Путь к .pcap (или 'live' для захвата): ").strip().strip('"')
    filter_expr = input("  Фильтр (напр. 'ip.addr == 192.168.1.1', 'tcp.port == 80'): ").strip()
    
    if not filter_expr:
        print_error(" Фильтр не указан!")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    if pcap_path.lower() == "live":
        print_info("Live-захват с фильтром...\n")
        
        if not check_tshark():
            return
        
        cmd = "tshark -D"
        stdout, _, _ = run_command(cmd)
        print("Интерфейсы:")
        print(stdout)
        
        iface_num = input("  Номер интерфейса: ").strip()
        cmd = f'tshark -i {iface_num} -Y "{filter_expr}" -V'
        
        try:
            subprocess.run(cmd, shell=True, check=True)
        except KeyboardInterrupt:
            print_warning("\n Захват остановлен.")
    else:
        if not os.path.exists(pcap_path):
            print_error(f" Файл не найден: {pcap_path}")
            if safe_input("  [Enter для продолжения...]") is None:
                sys.exit(0)
            return
        
        print_info(f'Фильтр: {filter_expr}\n')
        
        try:
            subprocess.run(f'tshark -r "{pcap_path}" -Y "{filter_expr}"', shell=True, check=True)
        except KeyboardInterrupt:
            pass
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Traffic filtered: {filter_expr}")


def live_monitor():
    """Мониторинг трафика в реальном времени"""
    print_info("Мониторинг сети в реальном времени...\n")
    print_warning(" Нажмите Ctrl+C для остановки.\n")
    
    if not check_tshark():
        return
    
    cmd = "tshark -D"
    stdout, _, _ = run_command(cmd)
    print("Интерфейсы:")
    print(stdout)
    
    iface_num = input("  Номер интерфейса: ").strip()
    
    print_info("Запуск мониторинга...\n")
    
    try:
        subprocess.run(f'tshark -i {iface_num} -c 100', shell=True, check=True)
        print_info("Захвачено 100 пакетов.")
    except KeyboardInterrupt:
        print_warning("\n Мониторинг остановлен.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Live monitoring executed")


def capture_dns():
    """Перехват DNS-запросов"""
    print_info("Перехват DNS-запросов\n")
    
    if not check_tshark():
        return
    
    pcap_path = input("  Сохранить в .pcap (пусто = нет): ").strip()
    
    if pcap_path.lower() == "yes" or pcap_path.lower() == "y":
        pcap_path = input("  Имя файла: ").strip() or "dns_capture.pcap"
        cmd = f'tshark -i any -Y "dns" -w "{pcap_path}" -V'
    else:
        cmd = 'tshark -i any -Y "dns" -T fields -e dns.qry.name -e dns.a'
    
    print_info("Перехват DNS-запросов...\n")
    print_info("Запрашиваемые домены:\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Перехват остановлен.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("DNS capture executed")


def capture_http():
    """Перехват HTTP-трафика"""
    print_info("Перехват HTTP-запросов\n")
    print_warning(" Внимание: HTTPS-трафик зашифрован и не будет виден!\n")
    
    if not check_tshark():
        return
    
    pcap_path = input("  Сохранить в .pcap (пусто = нет): ").strip()
    
    if pcap_path.lower() == "yes" or pcap_path.lower() == "y":
        pcap_path = input("  Имя файла: ").strip() or "http_capture.pcap"
        cmd = f'tshark -i any -Y "http.request" -T fields -e ip.src -e http.host -e http.request.uri -w "{pcap_path}"'
    else:
        cmd = 'tshark -i any -Y "http.request" -T fields -e ip.src -e http.host -e http.request.uri'
    
    print_info("Перехват HTTP-запросов...\n")
    print_info("Столбцы: IP-источник | Домен | URI\n")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print_warning("\n Перехват остановлен.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("HTTP capture executed")
