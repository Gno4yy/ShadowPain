"""
Email Module — Анонимная почта через Mail.tm API
Полностью автоматизировано — не требует установки дополнительных пакетов
"""

import json
import string
import random
import ssl
import urllib.request
import urllib.error
import urllib.parse
import os
import sys

# Добавляем корень проекта в путь при запуске напрямую
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from utils.helpers import (
    clear_screen, print_banner, print_success, print_error,
    print_info, print_warning, save_output, safe_input
)
from utils.logger import setup_logger

logger = setup_logger()

API_BASE = "https://api.mail.tm"

# Глобальные переменные для хранения текущего аккаунта
_current_account = None

# Кэш доменов
_cached_domains = []


def _get_domains():
    """Получение списка доступных доменов из API"""
    global _cached_domains
    
    if _cached_domains:
        return _cached_domains
    
    data, status = _make_request(f"{API_BASE}/domains")
    
    if status == 200:
        _cached_domains = [d.get("domain") for d in data.get("hydra:member", []) if d.get("isActive")]
    
    return _cached_domains


def _get_available_domain():
    """Получение первого доступного домена"""
    domains = _get_domains()
    if domains:
        return domains[0]
    return None


def _ssl_context():
    """Создание SSL контекста"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _make_request(url, data=None, headers=None, method=None):
    """HTTP запрос через urllib (без requests)"""
    ctx = _ssl_context()
    
    if headers is None:
        headers = {}
    
    # Добавляем Content-Type для POST/PUT/PATCH
    if data is not None and method in (None, "POST", "PUT", "PATCH"):
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
    
    if data is not None:
        if isinstance(data, dict):
            data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method or "POST")
    else:
        req = urllib.request.Request(url, headers=headers, method=method or "GET")
    
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        resp_data = resp.read().decode("utf-8")
        status = resp.status
        if resp_data:
            return json.loads(resp_data), status
        return {}, status
    except urllib.error.HTTPError as e:
        try:
            error_data = json.loads(e.read().decode("utf-8"))
        except Exception:
            error_data = {}
        return error_data, e.code
    except Exception as e:
        return {"error": str(e)}, 0


def _get_token():
    """Получение JWT-токена"""
    global _current_account
    if not _current_account or not _current_account.get("email"):
        return None
    
    email = _current_account["email"]
    password = _current_account["password"]
    
    data, status = _make_request(
        f"{API_BASE}/token",
        data={"address": email, "password": password}
    )
    
    if status == 200 and "token" in data:
        _current_account["token"] = data["token"]
        return data["token"]
    
    return None


def _get_headers():
    """Получение заголовков с токеном"""
    token = _get_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def generate_password(length=12):
    """Генерация случайного пароля"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))


def generate_username(length=8):
    """Генерация случайного юзернейма"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def run_email_module():
    """Модуль анонимной почты"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === Email: Анонимная почта (Mail.tm) ===\n")
        
        if _current_account and _current_account.get("email"):
            print(f"  [i] Активный аккаунт: {_current_account['email']}\n")
        
        print("  [1]  ⚡ Быстрое создание (автоматически)")
        print("  [2]  Проверить входящие")
        print("  [3]  Прочитать письмо")
        print("  [4]  ⚡ Отправить письмо (SMTP)")
        print("  [5]  Создать с выбором")
        print("  [6]  Удалить аккаунт")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            create_quick_account()
        elif choice == "2":
            check_inbox()
        elif choice == "3":
            read_message()
        elif choice == "4":
            send_smtp_message()
        elif choice == "5":
            create_account()
        elif choice == "6":
            delete_account()
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            input("  [Enter для продолжения...]")


def create_quick_account():
    """Моментальное создание анонимного аккаунта — полностью автоматически"""
    global _current_account
    print_info("Создание анонимного аккаунта...\n")
    
    # Получаем доступный домен
    domain = _get_available_domain()
    if not domain:
        print_error(" Нет доступных доменов. Попробуйте позже.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Генерация данных
    username = generate_username()
    password = generate_password()
    email = f"{username}@{domain}"
    
    # Создание аккаунта
    data, status = _make_request(
        f"{API_BASE}/accounts",
        data={"address": email, "password": password}
    )
    
    if status == 201:
        # Получаем токен
        token = _get_token()
        
        # Сохраняем аккаунт
        _current_account = {
            "email": email,
            "password": password,
            "token": token,
            "created": True
        }
        
        print_success(" Аккаунт создан!\n")
        print(f"  Email:    \033[92m{email}\033[0m")
        print(f"  Пароль:   {password}")
        print(f"  Токен:    {token[:30] if token else 'N/A'}...")
        print()
        
        # Сохраняем данные
        filepath = save_output(
            f"email_{username}.json",
            json.dumps(_current_account, indent=2, ensure_ascii=False)
        )
        print_info(f" Данные сохранены: {filepath}")
        print_info(" Проверьте входящие (пункт [2])\n")
        
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        logger.info(f"Quick email created: {email}")
    else:
        print_error(" Ошибка создания аккаунта:")
        print_error(json.dumps(data, indent=2, ensure_ascii=False))
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)


def check_inbox_auto():
    """Автоматическая проверка входящих (без input)"""
    token = _get_token()
    if not token:
        return []
    
    try:
        headers = _get_headers()
        data, status = _make_request(f"{API_BASE}/messages", headers=headers)
        
        if status == 200:
            messages = data.get("hydra:member", [])
            if messages:
                print_success(f" Найдено писем: {len(messages)}\n")
                for i, msg in enumerate(messages, 1):
                    print(f"  [{i}] От: {msg.get('from', {}).get('address', 'N/A')}")
                    print(f"      Тема: {msg.get('subject', 'Без темы')}")
                    print(f"      Дата: {msg.get('createdAt', 'N/A')}")
                    print()
            return messages
    except Exception:
        pass
    
    return []


def check_inbox():
    """Проверка входящих писем"""
    print_info("Проверка входящих...\n")
    
    token = _get_token()
    if not token:
        print_error(" Нет активного аккаунта. Создайте аккаунт сначала.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    try:
        headers = _get_headers()
        data, status = _make_request(f"{API_BASE}/messages", headers=headers)
        
        if status == 200:
            messages = data.get("hydra:member", [])
            
            if not messages:
                print_info(" Входящих писем нет.")
            else:
                print_success(f" Найдено писем: {len(messages)}\n")
                for i, msg in enumerate(messages, 1):
                    print(f"  [{i}] От: {msg.get('from', {}).get('address', 'N/A')}")
                    print(f"      Тема: {msg.get('subject', 'Без темы')}")
                    print(f"      Дата: {msg.get('createdAt', 'N/A')}")
                    print()
            
            return messages
        else:
            print_error(f" Ошибка: {status}")
            
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Checked inbox")


def read_message():
    """Чтение конкретного письма"""
    messages = check_inbox()
    if not messages:
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    try:
        idx = int(input("\n  Номер письма: ").strip()) - 1
        if 0 <= idx < len(messages):
            msg_id = messages[idx]["id"]
            headers = _get_headers()
            
            data, status = _make_request(
                f"{API_BASE}/messages/{msg_id}",
                headers=headers
            )
            
            if status == 200:
                print(f"\n  От: {data.get('from', {}).get('address', 'N/A')}")
                print(f"  Тема: {data.get('subject', 'N/A')}")
                print(f"  Дата: {data.get('createdAt', 'N/A')}")
                print(f"  Тело:\n  {'─' * 40}")
                print(data.get('text', data.get('html', 'Нет текста')))
                print(f"  {'─' * 40}")
            else:
                print_error(f" Ошибка чтения: {status}")
        else:
            print_error(" Неверный номер.")
    except ValueError:
        print_error(" Введите число.")
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info("Read message")


# SMTP-серверы для популярных провайдеров
SMTP_PROVIDERS = {
    "Gmail": ("smtp.gmail.com", 587),
    "Outlook": ("smtp-mail.outlook.com", 587),
    "Yandex": ("smtp.yandex.ru", 587),
    "Mail.ru": ("smtp.mail.ru", 587),
    "ProtonMail": ("smtp.protonmail.com", 587),
    "Свой SMTP": (None, None),
}


def send_smtp_message():
    """Отправка письма через SMTP"""
    print_info("Отправка письма через SMTP\n")
    
    # Выбор провайдера
    print("  Доступные SMTP-серверы:")
    for i, (name, _) in enumerate(SMTP_PROVIDERS.items(), 1):
        print(f"    [{i}]  {name}")
    print()
    
    choice = input("  Выбор провайдера (номер): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(SMTP_PROVIDERS):
            provider_name = list(SMTP_PROVIDERS.keys())[idx]
            smtp_host, smtp_port = SMTP_PROVIDERS[provider_name]
        else:
            print_error(" Неверный выбор.")
            if safe_input("  [Enter для продолжения...]") is None:
                sys.exit(0)
            return
    except ValueError:
        print_error(" Введите номер.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Свой SMTP
    if provider_name == "Свой SMTP":
        smtp_host = input("  SMTP-сервер (напр. smtp.gmail.com): ").strip()
        if not smtp_host:
            print_error(" SMTP-сервер не указан!")
            if safe_input("  [Enter для продолжения...]") is None:
                sys.exit(0)
            return
        try:
            smtp_port = int(input("  Порт (587): ").strip() or "587")
        except ValueError:
            smtp_port = 587
    else:
        print_info(f"  SMTP: {smtp_host}:{smtp_port}\n")
    
    # Данные аккаунта
    smtp_user = input("  Логин (email): ").strip()
    smtp_pass = input("  Пароль / App Password: ").strip()
    
    if not smtp_user or not smtp_pass:
        print_error(" Логин и пароль обязательны!")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    recipient = input("  Кому (email): ").strip()
    if not recipient or "@" not in recipient:
        print_error(" Неверный email получателя.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    subject = input("  Тема: ").strip()
    if not subject:
        print_error(" Тема не может быть пустой.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    print("  Введите текст письма (пустая строка для завершения):")
    lines = []
    while True:
        line = input("  > ")
        if line == "" and lines:
            break
        lines.append(line)
    
    body = "\n".join(lines)
    if not body.strip():
        print_error(" Текст письма не может быть пустым.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    # Отправка через SMTP
    print_info(f"Подключение к {smtp_host}:{smtp_port}...")
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        # Подключение и отправка
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, recipient, msg.as_string())
        server.quit()
        
        print_success(" Письмо отправлено!")
        print_info(f" От: {smtp_user}")
        print_info(f" Кому: {recipient}")
        print_info(f" Тема: {subject}")
        
    except smtplib.SMTPAuthenticationError:
        print_error(" Ошибка авторизации! Проверьте логин и пароль.")
        print_info(" Для Gmail нужен App Password:")
        print_info("  1. Настройки Google → Безопасность")
        print_info("  2. 2-шаговая проверка → App Passwords")
        print_info("  3. Создать пароль → скопировать")
    except smtplib.SMTPException as e:
        print_error(f" SMTP-ошибка: {e}")
    except Exception as e:
        print_error(f" Ошибка отправки: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Sent SMTP email to {recipient}: {subject}")


def create_account():
    """Создание аккаунта с выбором"""
    global _current_account
    print_info("Создание анонимного аккаунта...\n")
    
    # Получаем доступный домен
    domain = _get_available_domain()
    if not domain:
        print_error(" Нет доступных доменов. Попробуйте позже.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    username = generate_username()
    password = generate_password()
    email = f"{username}@{domain}"
    
    print_info(f"  Email: {email}")
    print_info(f"  Пароль: {password}\n")
    
    confirm = input("  Создать? (y/n): ").strip().lower()
    if confirm != 'y':
        print_info(" Отменено.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    data, status = _make_request(
        f"{API_BASE}/accounts",
        data={"address": email, "password": password}
    )
    
    if status == 201:
        token = _get_token()
        
        _current_account = {
            "email": email,
            "password": password,
            "token": token,
            "created": True
        }
        
        print_success(f"\n Аккаунт создан!")
        print(f"  Email: {email}")
        print(f"  Пароль: {password}")
        
        filepath = save_output(
            f"email_{username}.json",
            json.dumps(_current_account, indent=2, ensure_ascii=False)
        )
        print_info(f" Данные сохранены: {filepath}")
    else:
        print_error(f" Ошибка создания: {status}")
        print_error(json.dumps(data, indent=2, ensure_ascii=False))
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Created email account: {email}")


def delete_account():
    """Удаление аккаунта"""
    global _current_account
    if not _current_account or not _current_account.get("email"):
        print_error(" Нет активного аккаунта.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    email = _current_account["email"]
    password = _current_account["password"]
    
    confirm = input("  >>> ").strip().lower()
    if confirm != 'y':
        print_info(" Отменено.")
        if safe_input("  [Enter для продолжения...]") is None:
            sys.exit(0)
        return
    
    try:
        # Получаем токен
        data, status = _make_request(
            f"{API_BASE}/token",
            data={"address": email, "password": password}
        )
        
        if status == 200 and "token" in data:
            token = data["token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Получаем ID аккаунта
            data, status = _make_request(f"{API_BASE}/me", headers=headers)
            if status == 200 and "id" in data:
                account_id = data["id"]
                
                # Удаляем
                _, status = _make_request(
                    f"{API_BASE}/accounts/{account_id}",
                    headers=headers,
                    method="DELETE"
                )
                
                if status == 204:
                    print_success(" Аккаунт удалён.")
                    _current_account = None
                else:
                    print_error(f" Ошибка удаления: {status}")
            else:
                print_error(" Не удалось получить ID аккаунта.")
        else:
            print_error(" Ошибка авторизации.")
            
    except Exception as e:
        print_error(f" Ошибка: {e}")
    
    if safe_input("  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Deleted account: {email}")
