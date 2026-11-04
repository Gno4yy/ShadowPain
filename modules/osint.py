"""
OSINT Module — Поиск по никнейму
"""

import subprocess
import sys
import os
import json
import ssl
import urllib.request
import urllib.error
import re

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

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def sanitize_filename(name):
    """Очистка имени файла от недопустимых символов"""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def check_site(url, username, not_found_patterns=None):
    """Проверка сайта — возвращает (найден, final_url, статус)"""
    try:
        req = urllib.request.Request(url.format(username), headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="ignore")
        final_url = resp.geturl()
        
        if not_found_patterns:
            html_lower = html.lower()
            for pattern in not_found_patterns:
                if pattern.lower() in html_lower:
                    return False, url.format(username), resp.status
        
        return True, final_url, resp.status
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, url.format(username), e.code
        return False, url.format(username), e.code
    except urllib.error.URLError:
        return False, url.format(username), "network_error"
    except Exception:
        return False, url.format(username), "error"


# Определение для каждого сайта
SITE_CHECKS = {
    "GitHub": {
        "url": "https://github.com/{}",
        "not_found": ["there's nothing here", "there is nothing here", "sorry, nobody with this username"],
    },
    "Twitter/X": {
        "url": "https://x.com/{}",
        "not_found": ["user doesn't exist", "this account doesn't exist"],
    },
    "Instagram": {
        "url": "https://www.instagram.com/{}",
        "not_found": ["sorry_page_title", "the page you're looking for", "page you requested was not found"],
    },
    "Facebook": {
        "url": "https://www.facebook.com/{}",
        "not_found": ["sorry, this page isn't", "page not found"],
    },
    "YouTube": {
        "url": "https://youtube.com/@{}",
        "not_found": ["not found"],
    },
    "TikTok": {
        "url": "https://www.tiktok.com/@{}",
        "not_found": ["page not found"],
    },
    "Reddit": {
        "url": "https://www.reddit.com/user/{}",
        "not_found": ["page doesn't exist", "not found"],
    },
    "VK": {
        "url": "https://vk.com/{}",
        "not_found": ["страница не найдена", "page not found"],
    },
    "Telegram": {
        "url": "https://t.me/{}",
        "not_found": ["not found", "no such channel"],
    },
    "LinkedIn": {
        "url": "https://www.linkedin.com/in/{}",
        "not_found": ["not found"],
    },
    "Pinterest": {
        "url": "https://www.pinterest.com/{}",
        "not_found": ["not found"],
    },
    "Tumblr": {
        "url": "https://{}.tumblr.com",
        "not_found": ["not found"],
    },
    "DeviantArt": {
        "url": "https://www.deviantart.com/{}",
        "not_found": ["not found"],
    },
    "Flickr": {
        "url": "https://www.flickr.com/people/{}",
        "not_found": ["not found"],
    },
    "Steam": {
        "url": "https://steamcommunity.com/id/{}",
        "not_found": ["not found"],
    },
    "Minecraft": {
        "url": "https://namemc.com/profile/{}",
        "not_found": ["not found"],
    },
    "Spotify": {
        "url": "https://open.spotify.com/user/{}",
        "not_found": ["not found"],
    },
    "SoundCloud": {
        "url": "https://soundcloud.com/{}",
        "not_found": ["not found"],
    },
    "Discord": {
        "url": "https://discord.com/users/{}",
        "not_found": ["not found"],
    },
    "Medium": {
        "url": "https://medium.com/@{}",
        "not_found": ["not found"],
    },
    "Quora": {
        "url": "https://www.quora.com/profile/{}",
        "not_found": ["not found"],
    },
    "About.me": {
        "url": "https://about.me/{}",
        "not_found": ["not found"],
    },
    "Bitbucket": {
        "url": "https://bitbucket.org/{}",
        "not_found": ["not found"],
    },
    "Keybase": {
        "url": "https://keybase.io/{}",
        "not_found": ["not found"],
    },
    "HackerOne": {
        "url": "https://hackerone.com/{}",
        "not_found": ["not found"],
    },
    "HackTheBox": {
        "url": "https://app.hackthebox.com/profile/{}",
        "not_found": ["not found"],
    },
    # --- Социальные сети ---
    "X (старый)": {
        "url": "https://old.reddit.com/user/{}",
        "not_found": ["page doesn't exist", "not found"],
    },
    "Vimeo": {
        "url": "https://vimeo.com/{}",
        "not_found": ["not found", "page not found", "couldn't find the page"],
    },
    "Goodreads": {
        "url": "https://www.goodreads.com/{}",
        "not_found": ["not found", "page not found"],
    },
    "Last.fm": {
        "url": "https://www.last.fm/user/{}",
        "not_found": ["not found"],
    },
    "Twitch": {
        "url": "https://www.twitch.tv/{}",
        "not_found": ["not found", "page doesn't exist"],
    },
    "Snapchat": {
        "url": "https://www.snapchat.com/add/{}",
        "not_found": ["not found", "page not found"],
    },
    "Weibo": {
        "url": "https://weibo.com/{}",
        "not_found": ["not found"],
    },
    "Xiaohongshu": {
        "url": "https://www.xiaohongshu.com/user/profile/{}",
        "not_found": ["not found"],
    },
    # --- Форумы и сообщества ---
    "HackerNews": {
        "url": "https://news.ycombinator.com/user?id={}",
        "not_found": ["no such user"],
    },
    "StackOverflow": {
        "url": "https://stackoverflow.com/users?tab=profiles&q={}",
        "not_found": ["not found"],
    },
    "ProductHunt": {
        "url": "https://www.producthunt.com/@{}",
        "not_found": ["not found"],
    },
    "Dribbble": {
        "url": "https://dribbble.com/{}",
        "not_found": ["not found", "page not found"],
    },
    "Behance": {
        "url": "https://www.behance.net/{}",
        "not_found": ["not found", "page not found"],
    },
    "CodePen": {
        "url": "https://codepen.io/{}",
        "not_found": ["not found"],
    },
    "GitLab": {
        "url": "https://gitlab.com/{}",
        "not_found": ["not found", "page not found"],
    },
    "Codeforces": {
        "url": "https://codeforces.com/profile/{}",
        "not_found": ["not found"],
    },
    "LeetCode": {
        "url": "https://leetcode.com/{}",
        "not_found": ["not found"],
    },
    "Strava": {
        "url": "https://www.strava.com/athletes/{}",
        "not_found": ["not found"],
    },
    # --- Игровые платформы ---
    "EpicGames": {
        "url": "https://store.epicgames.com/u/{}",
        "not_found": ["not found"],
    },
    "GOG": {
        "url": "https://www.gog.com/forum/members/{}.1",
        "not_found": ["not found"],
    },
    "itch.io": {
        "url": "https://{}.itch.io",
        "not_found": ["not found", "page not found"],
    },
    "Roblox": {
        "url": "https://www.roblox.com/userprofile?username={}",
        "not_found": ["not found"],
    },
    "Rockstar": {
        "url": "https://socialclub.rockstargames.com/profile/{}",
        "not_found": ["not found", "profile not found"],
    },
    "Supercell": {
        "url": "https://supercell.com/en/games/clashofclans/leaderboard/{}",
        "not_found": ["not found"],
    },
    "PSNProfiles": {
        "url": "https://psnprofiles.com/search/?searchType=player&searchPlayer={}",
        "not_found": ["not found"],
    },
    "XboxGamertag": {
        "url": "https://xboxgamertag.com/search/{}",
        "not_found": ["not found"],
    },
    # --- Хостинг и контент ---
    "Imgur": {
        "url": "https://imgur.com/user/{}",
        "not_found": ["not found"],
    },
    "Replit": {
        "url": "https://replit.com/@{}",
        "not_found": ["not found"],
    },
    "Codeberg": {
        "url": "https://codeberg.org/{}",
        "not_found": ["not found"],
    },
    "SourceForge": {
        "url": "https://sourceforge.net/u/{}",
        "not_found": ["not found"],
    },
    # --- Аудио и видео ---
    "Bandcamp": {
        "url": "https://bandcamp.com/{}",
        "not_found": ["not found"],
    },
    "Mixcloud": {
        "url": "https://www.mixcloud.com/{}",
        "not_found": ["not found"],
    },
    "PodcastIndex": {
        "url": "https://podcastindex.org/podcast/{}",
        "not_found": ["not found"],
    },
    # --- Приватность и крипто ---
    "NameID": {
        "url": "https://nameid.io/{}",
        "not_found": ["not found"],
    },
    "Shutterfly": {
        "url": "https://www.shutterfly.com/{}",
        "not_found": ["not found"],
    },
    "Gravatar": {
        "url": "https://en.gravatar.com/{}",
        "not_found": ["not found"],
    },
    "Foursquare": {
        "url": "https://foursquare.com/{}",
        "not_found": ["not found"],
    },
    "500px": {
        "url": "https://500px.com/p/{}",
        "not_found": ["not found"],
    },
    "Unsplash": {
        "url": "https://unsplash.com/@{}",
        "not_found": ["not found"],
    },
    "Pexels": {
        "url": "https://www.pexels.com/@{}",
        "not_found": ["not found"],
    },
    # --- Российские сервисы ---
    "Durov": {
        "url": "https://durov.com/{}",
        "not_found": ["not found"],
    },
    "Slavsearch": {
        "url": "https://slavsearch.org/search?q={}",
        "not_found": ["not found"],
    },
    # --- Профессиональные ---
    "AngelList": {
        "url": "https://angel.co/{}",
        "not_found": ["not found"],
    },
    "Crunchbase": {
        "url": "https://www.crunchbase.com/person/{}",
        "not_found": ["not found"],
    },
    "ResearchGate": {
        "url": "https://www.researchgate.net/profile/{}",
        "not_found": ["not found"],
    },
    "ORCID": {
        "url": "https://orcid.org/{}",
        "not_found": ["not found"],
    },
    # --- Мессенджеры и общение ---
    "Skype": {
        "url": "https://skype.com/user/{}",
        "not_found": ["not found"],
    },
    "Line": {
        "url": "https://line.me/ti/p/{}",
        "not_found": ["not found"],
    },
    "KakaoTalk": {
        "url": "https://open.kakao.com/o/{}/",
        "not_found": ["not found"],
    },
    "Telegram (канал)": {
        "url": "https://t.me/{}",
        "not_found": ["no such channel"],
    },
    # --- Блоги и статьи ---
    "LiveJournal": {
        "url": "https://{}.livejournal.com",
        "not_found": ["not found", "page not found"],
    },
    "Blogger": {
        "url": "https://{}.blogspot.com",
        "not_found": ["not found"],
    },
    "Substack": {
        "url": "https://{}.substack.com",
        "not_found": ["not found", "page not found"],
    },
    "Mirror": {
        "url": "https://{}.mirror.xyz",
        "not_found": ["not found"],
    },
    # --- Маркетплейсы ---
    "Etsy": {
        "url": "https://www.etsy.com/shop/{}",
        "not_found": ["not found", "page not found"],
    },
    "eBay": {
        "url": "https://www.ebay.com/usr/{}",
        "not_found": ["not found"],
    },
    "POSMarket": {
        "url": "https://pos.market/user/{}",
        "not_found": ["not found"],
    },
    # --- Дизайн и креатив ---
    "DeviantArt2": {
        "url": "https://www.deviantart.com/{}",
        "not_found": ["not found"],
    },
    "ArtStation": {
        "url": "https://www.artstation.com/{}",
        "not_found": ["not found"],
    },
    "Pixiv": {
        "url": "https://www.pixiv.net/en/users/{}",
        "not_found": ["not found"],
    },
    "Nijie": {
        "url": "https://nijie.info/members.php?id={}",
        "not_found": ["not found"],
    },
    # --- Безопасность и хакерские ---
    "Pastebin": {
        "url": "https://pastebin.com/u/{}",
        "not_found": ["not found"],
    },
    "HaveIBeenPwned": {
        "url": "https://haveibeenpwned.com/account/{}",
        "not_found": ["not found"],
    },
    "TryHackMe": {
        "url": "https://tryhackme.com/p/{}",
        "not_found": ["not found"],
    },
    "CTFtime": {
        "url": "https://ctftime.org/user/{}",
        "not_found": ["not found"],
    },
    # --- Видео и стриминг ---
    "Odysee": {
        "url": "https://odysee.com/@{}",
        "not_found": ["not found"],
    },
    "Rumble": {
        "url": "https://rumble.com/user/{}",
        "not_found": ["not found"],
    },
    "TikTok (alt)": {
        "url": "https://www.tiktok.com/@{}",
        "not_found": ["page not found"],
    },
    # --- Друзья и знакомства ---
    "Tinder": {
        "url": "https://tinder.com/@{}",
        "not_found": ["not found"],
    },
    "Badoo": {
        "url": "https://badoo.com/profile/{}",
        "not_found": ["not found"],
    },
    # --- Файлообменники ---
    "GoogleDrive": {
        "url": "https://drive.google.com/drive/u/0/search?q=folder:{}",
        "not_found": ["not found"],
    },
}


def run_osint_module():
    """Модуль OSINT — поиск аккаунтов по никнейму"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === OSINT: Поиск по никнейму ===\n")
        print("  [1]  Поиск (автоматический)")
        print("  [2]  Быстрый поиск (встроенный)")
        print("  [0]  Назад\n")
        
        choice = input("  >>> Ваш выбор: ").strip()
        
        if choice == "1":
            username = input("\n  Введите никнейм: ").strip()
            if not username:
                print_error("Никнейм не может быть пустым!")
                if safe_input("  [Enter для продолжения...]") is None:
                    sys.exit(0)
                continue
            search_auto(username)
        elif choice == "2":
            username = input("\n  Введите никнейм: ").strip()
            if not username:
                print_error("Никнейм не может быть пустым!")
                if safe_input("  [Enter для продолжения...]") is None:
                    sys.exit(0)
                continue
            quick_search(username)
        elif choice == "0":
            break
        else:
            print_error("Неверный выбор.")
            if safe_input("  [Enter для продолжения...]") is None:
                sys.exit(0)


def search_auto(username):
    """Автоматический поиск — сначала Sherlock, если не работает — быстрый поиск"""
    print_info(f"Поиск аккаунтов для: {username}")
    print_info("Попытка установить Sherlock...\n")
    
    installed = False
    
    # 1. Ставим зависимости через python -m pip
    print_info("Устанавливаем зависимости...")
    run_command(f'{sys.executable} -m pip install requests colorama prettytable tldextract')
    
    # 2. Пробуем стандартную установку
    print_info("Устанавливаем Sherlock...")
    stdout, stderr, rc = run_command(f'{sys.executable} -m pip install sherlock-project')
    
    if rc != 0:
        # 3. Пробуем без pandas
        print_info("  Пробуем без pandas...")
        run_command(f'{sys.executable} -m pip uninstall pandas -y')
        stdout, stderr, rc = run_command(f'{sys.executable} -m pip install sherlock-project')
    
    if rc == 0 and check_tool("sherlock"):
        installed = True
        print_success("  Sherlock установлен!\n")
    
    # 4. Запускаем Sherlock
    if installed:
        print_info("Запускаем Sherlock...\n")
        cmd = f'sherlock --print-all "{username}"'
        stdout, stderr, returncode = run_command(cmd)
        output = stdout + stderr
        
        if output.strip():
            print_success("Результаты Sherlock:\n")
            print(output)
            filepath = save_output(f"osint_{sanitize_filename(username)}_sherlock.txt", output)
            print_info(f"Сохранено в: {filepath}")
            if safe_input("\n  [Enter для продолжения...]") is None:
                sys.exit(0)
            logger.info(f"OSINT search completed for: {username} (Sherlock)")
            return
    
    # 5. Sherlock не работает — автоматически переходим к быстрому поиску
    print_warning("  Sherlock недоступен. Переход к быстрому поиску...\n")
    quick_search(username)


def quick_search(username):
    """Быстрый поиск по никнейму"""
    print_info(f"Быстрый поиск по никнейму: {username}\n")
    print_info(f"Проверка {len(SITE_CHECKS)} сайтов...\n")
    
    results = []
    found = 0
    errors = 0
    
    for i, (site_name, site_info) in enumerate(SITE_CHECKS.items(), 1):
        check_url_str = site_info["url"].format(username)
        
        # Показываем прогресс
        sys.stdout.write(f'\r  [{i}/{len(SITE_CHECKS)}] {site_name:15s} ...')
        sys.stdout.flush()
        
        try:
            not_found_patterns = site_info.get("not_found", [])
            is_found, final_url, status = check_site(site_info["url"], username, not_found_patterns)
            
            if is_found:
                results.append((site_name, final_url, "Найден"))
                found += 1
            else:
                results.append((site_name, check_url_str, f"HTTP {status}" if isinstance(status, int) else status))
                if status in ("network_error", "error"):
                    errors += 1
        except Exception:
            results.append((site_name, check_url_str, "Ошибка"))
            errors += 1
    
    print()  # новая строка после прогресса
    
    # Вывод результатов
    clear_screen()
    print_banner()
    print(f"\n  === Результаты поиска: {username} ===\n")
    print(f"  Найдено: {found}/{len(SITE_CHECKS)}  |  Ошибок: {errors}\n")
    
    if found > 0:
        print("  \033[92mНайдены:\033[0m")
        for site, url, status in results:
            if status == "Найден":
                print(f"  \033[92m[+]\033[0m  {site:18s} → {url}")
        
        print()
        not_found = [r for r in results if r[2] != "Найден"]
        if not_found:
            print("  \033[91mНе найдены:\033[0m")
            for site, url, status in not_found:
                print(f"  \033[91m[-]\033[0m  {site:18s} → {url}")
    else:
        print("  Аккаунты не найдены на проверенных сайтах.")
    
    # Сохраняем результат
    output_text = f"Поиск: {username}\nНайдено: {found}/{len(SITE_CHECKS)}\nОшибок: {errors}\n\n"
    for site, url, status in results:
        marker = "[+]" if status == "Найден" else "[-]"
        output_text += f"{marker} {site:18s} → {url}\n"
    
    filepath = save_output(f"osint_{sanitize_filename(username)}.txt", output_text)
    print_info(f"Результат сохранён в: {filepath}")
    
    if safe_input("\n  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Quick search completed for: {username}, found: {found}, errors: {errors}")
