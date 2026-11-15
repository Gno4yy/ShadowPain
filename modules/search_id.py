"""
Search by Unique ID Module
"""

import re
import urllib.request
import ssl
import urllib.parse
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def detect_id_type(id_value):
    """Определение типа ID по формату"""
    id_clean = id_value.strip()
    
    # YouTube User ID
    if re.match(r'^UC[a-zA-Z0-9_-]{22}$', id_clean):
        return "youtube_channel"
    if re.match(r'^@[a-zA-Z0-9_-]+$', id_clean):
        return "youtube_handle"
    if re.match(r'^[a-zA-Z0-9_-]{11}$', id_clean):
        # YouTube Video ID
        if re.match(r'^[a-zA-Z0-9_-]{11}$', id_clean):
            return "youtube_video"
    
    # Telegram Username
    if re.match(r'^@[a-zA-Z0-9_]{5,32}$', id_clean):
        return "telegram_username"
    if re.match(r'^[a-zA-Z0-9_]{5,32}$', id_clean):
        return "telegram_username"
    
    # VK User ID
    if re.match(r'^u[0-9]+$', id_clean):
        return "vk_user"
    if re.match(r'^[0-9]+$', id_clean) and len(id_clean) <= 10:
        return "vk_user"
    
    # Discord User ID (17-20 digits)
    if re.match(r'^\d{17,20}$', id_clean):
        return "discord"
    
    # Steam ID (64-bit)
    if re.match(r'^\d{17}$', id_clean):
        return "steam"
    
    # Twitch Username
    if re.match(r'^[a-zA-Z0-9_]{3,25}$', id_clean):
        return "twitch"
    
    # Twitter/X Username
    if re.match(r'^@[a-zA-Z0-9_]{1,15}$', id_clean):
        return "twitter"
    if re.match(r'^[a-zA-Z0-9_]{1,15}$', id_clean):
        return "twitter"
    
    # GitHub Username
    if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,38}[a-zA-Z0-9]$', id_clean):
        return "github"
    
    # Generic username
    return "generic"


def search_vk(id_value):
    """Поиск по VK ID"""
    results = []
    id_clean = id_value.strip().lstrip('u')
    
    if not id_clean.isdigit():
        # Поиск по username
        url = f"https://vk.com/{id_clean}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            if resp.status == 200:
                html = resp.read().decode("utf-8", errors="ignore")
                if "page_not_found" not in html.lower():
                    results.append({
                        "service": "VK",
                        "url": url,
                        "found": True,
                        "note": "Профиль VK найден"
                    })
        except Exception:
            pass
    else:
        # Поиск по ID
        url = f"https://vk.com/id{id_clean}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            if resp.status == 200:
                html = resp.read().decode("utf-8", errors="ignore")
                if "page_not_found" not in html.lower():
                    results.append({
                        "service": "VK",
                        "url": url,
                        "found": True,
                        "note": f"Профиль VK (id={id_clean}) найден"
                    })
        except Exception:
            pass
    
    return results


def search_telegram(id_value):
    """Поиск по Telegram username"""
    results = []
    id_clean = id_value.strip().lstrip('@')
    
    url = f"https://t.me/{id_clean}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=5, context=ctx)
        if resp.status == 200:
            results.append({
                "service": "Telegram",
                "url": url,
                "found": True,
                "note": f"Аккаунт Telegram (@{id_clean}) найден"
            })
    except Exception:
        pass
    
    return results


def search_youtube(id_value):
    """Поиск по YouTube ID"""
    results = []
    id_clean = id_value.strip()
    
    if id_clean.startswith("@"):
        # Handle
        url = f"https://youtube.com/{id_clean}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            if resp.status == 200:
                results.append({
                    "service": "YouTube",
                    "url": url,
                    "found": True,
                    "note": f"Канал YouTube (@{id_clean}) найден"
                })
        except Exception:
            pass
    elif id_clean.startswith("UC"):
        # Channel ID
        url = f"https://youtube.com/channel/{id_clean}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            if resp.status == 200:
                results.append({
                    "service": "YouTube",
                    "url": url,
                    "found": True,
                    "note": f"Канал YouTube (UC...) найден"
                })
        except Exception:
            pass
    elif len(id_clean) == 11:
        # Video ID
        url = f"https://youtube.com/watch?v={id_clean}"
        results.append({
            "service": "YouTube",
            "url": url,
            "found": True,
            "note": "Возможно, это ID видео"
        })
    
    return results


def search_discord(id_value):
    """Поиск по Discord ID"""
    results = []
    
    if re.match(r'^\d{17,20}$', id_value):
        # Discord ID можно проверить через Discord API (неофициально)
        results.append({
            "service": "Discord",
            "url": f"https://discord.com/users/{id_value}",
            "found": True,
            "note": "Discord User ID найден"
        })
    
    return results


def search_generic(id_value):
    """Общий поиск по никнейму/ID"""
    from modules.osint import quick_search
    results = []
    
    results.append({
        "service": "Multi-Platform Search",
        "url": "N/A",
        "found": True,
        "note": "Запуск быстрого поиска по всем платформам"
    })
    
    return results


def search_by_unique_id():
    """Поиск по уникальному ID (VK, Telegram, YouTube и др.)"""
    from utils.helpers import clear_screen, print_banner, print_info, print_success, print_warning, print_error, save_output, safe_input
    
    clear_screen()
    print_banner()
    print("  === Поиск по уникальному ID ===\n")
    print("  Поддерживаемые форматы:\n")
    print("  • VK: username или id (u123456789)")
    print("  • Telegram: @username или username")
    print("  • YouTube: @handle, UC..., или ID видео (11 символов)")
    print("  • Discord: User ID (17-20 цифр)")
    print("  • Twitch: username")
    print("  • Twitter/X: @username или username")
    print("  • GitHub: username")
    print("  • Любой другой: общий поиск по никнейму\n")
    
    id_value = input("  Введите ID/никнейм: ").strip()
    if not id_value:
        print_error("ID не может быть пустым!")
        if safe_input("  [Enter для продолжения...]") is None:
            import sys
            sys.exit(0)
        return
    
    # Определение типа
    id_type = detect_id_type(id_value)
    print_info(f"Определённый тип: {id_type}\n")
    
    results = []
    
    # Поиск в зависимости от типа
    if id_type in ("vk_user",):
        results.extend(search_vk(id_value))
    
    if id_type in ("telegram_username",):
        results.extend(search_telegram(id_value))
    
    if id_type in ("youtube_channel", "youtube_handle", "youtube_video"):
        results.extend(search_youtube(id_value))
    
    if id_type == "discord":
        results.extend(search_discord(id_value))
    
    if id_type == "generic":
        results.extend(search_generic(id_value))
    
    # Вывод результатов
    if results:
        print_success("Результаты поиска:\n")
        for r in results:
            if r.get("note") == "Запуск быстрого поиска по всем платформам":
                print_info(f"  [!] {r['note']}")
                print_info(f"  Введите никнейм для поиска:\n")
                username = input("  >>> ").strip()
                if username:
                    quick_search(username)
                return
            else:
                print_success(f"  [+] {r['service']}: {r['url']}")
                print_info(f"      {r['note']}")
    else:
        print_warning("  Аккаунты не найдены")
    
    # Дополнительные ресурсы
    print_info("\nДополнительные ресурсы:\n")
    id_clean = id_value.strip().lstrip('@')
    
    extra = [
        ("NameCheckr", f"https://namecheckr.com/search/{urllib.parse.quote(id_clean)}"),
        ("NameCheck", f"https://namechk.com/names/{urllib.parse.quote(id_clean)}"),
        ("KnowEm", f"https://knowem.com/"),
    ]
    for service, url in extra:
        print_info(f"  [{service}] {url}")
    
    # Сохранение результатов
    output = f"Поиск по ID: {id_value}\n"
    output += f"Тип ID: {id_type}\n\n"
    output += "Результаты:\n"
    for r in results:
        output += f"  [+] {r['service']}: {r['url']}\n"
        output += f"      {r['note']}\n"
    
    filepath = save_output(f"id_{id_clean}.txt", output)
    print_info(f"\nРезультат сохранён в: {filepath}")
    
    if safe_input("\n  [Enter для продолжения...]") is None:
        import sys
        sys.exit(0)

