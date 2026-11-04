"""
Tor Module — Настройка и проверка Tor-трафика
"""

import subprocess
import sys
import os
import socket
import time

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


def run_tor_module():
    """Модуль работы с Tor"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === Tor: Анонимность и настройка ===\n")
        print("  [1]  Проверить текущий IP")
        print("  [2]  Проверить Tor-соединение")
        print("  [3]  Перезагрузить Tor-идентичность")
        print("  [4]  Настроить прокси для Python")
        print("  [5]  Быстрый HTTP-запрос через Tor")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            check_current_ip()
        elif choice == "2":
            check_tor_connection()
        elif choice == "3":
            rotate_tor_identity()
        elif choice == "4":
            setup_python_proxy()
        elif choice == "5":
            quick_tor_request()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            input("  [Enter для продолжения...]")


def check_current_ip():
    """Проверка текущего IP-адреса"""
    print_info("Проверка IP-адреса...")
    
    try:
        import urllib.request
        ip = urllib.request.urlopen('https://api.ipify.org').read().decode()
        print_success(f" Ваш публичный IP: {ip}")
    except Exception as e:
        print_error(f" Не удалось определить IP: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Checked current IP")


def check_tor_connection():
    """Проверка работы Tor-соединения"""
    print_info("Проверка Tor-соединения...")
    
    # Проверяем SOCKS-прокси
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 9050))
        sock.close()
        
        if result == 0:
            print_success(" Tor-демон работает (порт 9050 открыт)")
        else:
            print_warning(" Tor-демон НЕ работает (порт 9050 закрыт)")
            print_info(" Убедитесь, что Tor установлен и запущен.")
    except Exception as e:
        print_error(f" Ошибка проверки: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Checked Tor connection")


def rotate_tor_identity():
    """Перезагрузка Tor-идентичности (новый IP)"""
    print_info("Запрос новой Tor-идентичности...")
    print_info("Это может занять 10-30 секунд...")
    
    # Способ 1: Через контрольный порт
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 9051))
        sock.close()
        
        if result == 0:
            # Отправляем сигнал NEWNYM
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('127.0.0.1', 9051))
            sock.sendall(b"AUTHENTICATE \"\"\r\nSIGNAL NEWNYM\r\n")
            time.sleep(2)
            sock.close()
            print_success(" Tor-идентичность обновлена!")
        else:
            print_warning(" Контрольный порт недоступен.")
            print_info(" Убедитесь, что Tor запущен с настроенным контрольным портом.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
        print_info(" Альтернатива: перезапустите службу Tor вручную.")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Rotated Tor identity")


def setup_python_proxy():
    """Настройка SOCKS-прокси для Python"""
    print_info("Настройка прокси для Python-скриптов\n")
    
    proxy_code = '''
# Добавьте этот код в ваш Python-скрипт:

import requests

# Настройка SOCKS-прокси через Tor
proxies = {
    "http": "socks5h://127.0.0.1:9050",
    "https": "socks5h://127.0.0.1:9050"
}

# Пример запроса через Tor
response = requests.get("https://httpbin.org/ip", proxies=proxies)
print(response.json())

# Для urllib:
import urllib.request
proxy = urllib.request.ProxyHandler({"http": "socks5h://127.0.0.1:9050"})
opener = urllib.request.build_opener(proxy)
urllib.request.install_opener(opener)
'''
    
    print(proxy_code)
    print_info("Установите PySocks: pip install PySocks\n")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Displayed Python proxy setup")


def quick_tor_request():
    """Быстрый HTTP-запрос через Tor"""
    print_info("Быстрый запрос через Tor...\n")
    
    try:
        import requests
        
        proxies = {
            "http": "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050"
        }
        
        print_info("Запрос через Tor...")
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f" Tor-IP: {data.get('origin', 'N/A')}")
        else:
            print_error(f" Статус: {response.status_code}")
            
    except ImportError:
        print_warning(" requests не установлен. Используем urllib...\n")
        try:
            import urllib.request
            proxy = urllib.request.ProxyHandler({
                "http": "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050"
            })
            opener = urllib.request.build_opener(proxy)
            urllib.request.install_opener(opener)
            response = urllib.request.urlopen("https://api.ipify.org", timeout=30)
            ip = response.read().decode()
            print_success(f" Tor-IP: {ip}")
        except Exception as e2:
            print_error(f" Ошибка: {e2}")
            print_info(" Убедитесь, что Tor запущен на порту 9050.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
        print_info(" Убедитесь, что Tor запущен на порту 9050.")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Quick Tor request executed")
