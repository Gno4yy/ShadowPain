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
import asyncio

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

# --- Настройки async-поиска ---
MAX_CONCURRENCY = 100       # макс. параллельных запросов
REQUEST_TIMEOUT = 8         # таймаут на один сайт (сек)
TOTAL_TIMEOUT = 120         # общий таймаут всего поиска (сек)


def sanitize_filename(name):
    """Очистка имени файла от недопустимых символов"""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


# ============================================================
# Максимально точная детекция: позитивная + негативная марки
# ============================================================

# Паттерны для извлечения заголовка страницы
_TITLE_PATTERNS = [
    re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<meta\s+(?:name="og:title"|property="og:title"|name="twitter:title")\s+content="([^"]*)"', re.IGNORECASE),
]

# --- НЕГАТИВНЫЕ маркеры (страница НЕ найдена) ---
# ТОЛЬКО специфичные фразы, которые гарантированно означают "not found"
_NOT_FOUND_TITLE_PATTERNS = [
    "user not found",
    "this account doesn't exist",
    "this page isn't available",
    "sorry, this page isn't",
    "page not found",
    "page doesn't exist",
    "couldn't find the page",
    "no such user",
    "no such account",
    "account not found",
    "profile not found",
    "doesn't exist",
    "does not exist",
    "no results for",
    "no matching results",
    "we couldn't find",
    "404",
    "why not available",
]

# Паттерны страниц логина/авторизации (тоже НЕ профиль)
_LOGIN_PAGE_PATTERNS = [
    "login",
    "sign in",
    "authenticate",
    "authorization",
    "sign up",
    "register",
    "create account",
    "log in",
]

# Паттерны страниц поиска (НЕ профиль)
_SEARCH_PAGE_PATTERNS = [
    "search results",
    "search for",
    "find",
]

# Паттерны "not found" для проверки в заголовке (на русском)
_NOT_FOUND_TITLE_PATTERNS_RU = [
    "страница не найдена",
    "страница не существует",
    "пользователь не найден",
]

# --- ПОЗИТИВНЫЕ маркеры (страница НАЙДЕНА) ---
# Слова, которые почти гарантированно есть на странице профиля
_PROFILE_TITLE_KEYWORDS = [
    "profile", "профиль",
    "posts", "подписчиков", "followers",
    "about", "об", "bio",
    "member since", "registered",
]

# --- HTML-элементы, указывающие на страницу профиля ---
_PROFILE_HTML_MARKERS = [
    re.compile(r'<meta\s+property="og:url"\s+content="[^"]*{}"', re.IGNORECASE),
    re.compile(r'<meta\s+name="og:url"\s+content="[^"]*{}"', re.IGNORECASE),
    re.compile(r'itemtype="https://schema.org/Person"', re.IGNORECASE),
    re.compile(r'class="[^"]*avatar[^"]*"', re.IGNORECASE),
    re.compile(r'<img[^>]*class="[^"]*avatar[^"]*"', re.IGNORECASE),
    re.compile(r'aria-label="[^"]*follower[^"]*"', re.IGNORECASE),
    re.compile(r'data-testid="UserProfileHeader_Items"', re.IGNORECASE),
    re.compile(r'property="og:description"', re.IGNORECASE),
]

# --- HTML-элементы, указывающие на "not found" ---
_NOT_FOUND_HTML_MARKERS = [
    re.compile(r'<h1[^>]*>page not found</h1>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<h1[^>]*>not found</h1>', re.IGNORECASE | re.DOTALL),
    re.compile(r'aria-label="not.?found"', re.IGNORECASE),
]

# --- Редиректы на главную страницу (признак "not found") ---
# Если final_url перешёл на главную — это признак что профиль не найден
_REDIRECT_TO_HOME_PATTERNS = [
    re.compile(r'^https?://[^/]+/[^/\?]+$', re.IGNORECASE),  # Просто домен без пути
]

# --- Маркеры в URL, указывающие на "not found" или страницу логина ---
# Если URL содержит эти слова — это НЕ профиль
_URL_NOT_FOUND_PATTERNS = [
    # Ошибки
    "/404",
    "/error",
    "/not-found",
    # Spotify
    "why-not-available",
    # Страницы логина
    "/login",
    "/signin",
    "/sign-in",
    "/authenticate",
    "/authorization",
    "/auth",
    # Страницы регистрации
    "/signup",
    "/sign-up",
    "/register",
    # Страницы поиска
    "?q=",
    "&q=",
    "/search?",
    "/search?",
]

# --- Специфичные паттерны для каждого сайта ---
# Только для сайтов с уникальной логикой "not found"
# Большинство сайтов обрабатываются через общие правила (title, URL)
SITE_SPECIFIC_NOT_FOUND = {
    "VK": ["вход", "регистрация"],  # Страница входа
    "SoundCloud": ["stream", "listen", "songs"],  # Страница поиска/стриминга
    "Slavsearch": ["search"],  # Страница поиска
    "PSNProfiles": ["search"],  # Страница поиска
    "XboxGamertag": ["search"],  # Страница поиска
}


def _extract_page_title(html):
    """Извлекает заголовок страницы из HTML (<title> или meta-теги)."""
    for pattern in _TITLE_PATTERNS:
        match = pattern.search(html)
        if match:
            title = match.group(1).strip()
            if title:
                return title
    return None


def _check_redirect_to_home(original_url, final_url):
    """Проверяет, был ли редирект на главную страницу (признак 'not found')."""
    if original_url == final_url:
        return False
    
    # Если final_url — просто домен без пути (или с пустым путём)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(final_url)
        path = parsed.path.rstrip('/')
        if not path or path == '/':
            return True
    except Exception:
        pass
    return False


def _score_profile(html, username, original_url=None, final_url=None, site_name=None):
    """Оценивает вероятность что страница — найденный профиль.
    
    Возвращает:
        1  — уверенно НАЙДЕН (позитивные маркеры)
       -1  — уверенно НЕ НАЙДЕН (негативные маркеры)
        0  — неопределённо
    """
    title = _extract_page_title(html)
    title_lower = title.lower() if title else ""
    html_lower = html.lower()
    username_lower = username.lower()
    
    # === ШАГ 1: Проверяем негативные маркеры (уверенное NOT FOUND) ===
    
    # Проверка URL на наличие маркеров ошибок/логина
    if final_url:
        final_url_lower = final_url.lower()
        for pattern in _URL_NOT_FOUND_PATTERNS:
            if pattern.lower() in final_url_lower:
                return -1  # NOT FOUND (URL содержит маркер ошибки/логина)
    
    # Специфичные паттерны для каждого сайта
    if site_name and site_name in SITE_SPECIFIC_NOT_FOUND:
        for pattern in SITE_SPECIFIC_NOT_FOUND[site_name]:
            if pattern.lower() in html_lower:
                return -1  # NOT FOUND (специфичный паттерн сайта)
    
    # Негативные паттерны в title — самый надёжный индикатор
    for pattern in _NOT_FOUND_TITLE_PATTERNS:
        if pattern.lower() in title_lower:
            return -1  # NOT FOUND
    
    for pattern in _NOT_FOUND_TITLE_PATTERNS_RU:
        if pattern.lower() in title_lower:
            return -1  # NOT FOUND
    
    # Негативные HTML-маркеры
    for marker in _NOT_FOUND_HTML_MARKERS:
        if marker.search(html):
            return -1  # NOT FOUND
    
    # Проверка страниц логина/авторизации
    for pattern in _LOGIN_PAGE_PATTERNS:
        if pattern.lower() in title_lower:
            return -1  # NOT FOUND (страница логина)
    
    # Проверка страниц поиска
    for pattern in _SEARCH_PAGE_PATTERNS:
        if pattern.lower() in title_lower:
            return -1  # NOT FOUND (страница поиска)
    
    # Проверка og:url — если meta og:url не содержит username, это признак "not found"
    og_url_match = re.search(r'<meta\s+(?:property|name)="og:url"\s+content="([^"]*)"', html, re.IGNORECASE)
    if og_url_match:
        og_url = og_url_match.group(1).lower()
        # Если og:url не содержит username — это главная страница или ошибка
        if username_lower not in og_url:
            # Но если og:url — это просто домен (главная), то это точно not found
            if _check_redirect_to_home(original_url, og_url_match.group(1)):
                return -1  # NOT FOUND
    
    # Проверка редиректа на главную страницу
    if original_url and final_url:
        if _check_redirect_to_home(original_url, final_url):
            return -1  # NOT FOUND (редирект на главную = профиль не найден)
    
    # === ШАГ 2: Проверяем позитивные маркеры (уверенное FOUND) ===
    
    score = 0
    
    # КРИТИЧЕСКИ ВАЖНО: username должен быть И в title, И в URL
    # Если username только в title, но не в URL — это скорее всего главная страница
    url_has_username = False
    if final_url and username_lower in final_url.lower():
        url_has_username = True
    
    if url_has_username:
        # Username в title + в URL — сильный признак
        if username_lower in title_lower:
            score += 3
    else:
        # Username только в title (не в URL) — слабый признак
        if username_lower in title_lower:
            score += 1
    
    # Profile-ключевые слова в title
    for kw in _PROFILE_TITLE_KEYWORDS:
        if kw.lower() in title_lower:
            score += 1
    
    # URL-маркеры: meta og:url содержит username
    for marker in _PROFILE_HTML_MARKERS:
        if marker.search(html):
            score += 2
    
    # HTML-маркеры профиля
    if re.search(r'avatar', html_lower):
        score += 1
    if re.search(r'follower', html_lower):
        score += 1
    if re.search(r'post', html_lower):
        score += 1
    
    # === ШАГ 3: Решаем по баллам ===
    if score >= 2:
        return 1  # FOUND
    if score <= -1:
        return -1  # NOT FOUND
    
    return 0  # Неопределённо


def check_site(url, username, not_found_patterns=None):
    """Проверка сайта — возвращает (найден, final_url, статус)"""
    try:
        req = urllib.request.Request(url.format(username), headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        html = resp.read().decode("utf-8", errors="ignore")
        final_url = resp.geturl()
        status = resp.status
        
        # 1. Приоритет: HTTP 404 = уверенно NOT FOUND
        if status == 404:
            return False, url.format(username), status
        
        # 2. Основной анализ: позитивные + негативные маркеры
        score = _score_profile(html, username, url.format(username), final_url)
        if score == 1:
            return True, final_url, status
        if score == -1:
            return False, final_url, status
        
        # 3. Fallback: старые паттерны в полном HTML
        if not_found_patterns:
            html_lower = html.lower()
            for pattern in not_found_patterns:
                if pattern.lower() in html_lower:
                    return False, url.format(username), status
        
        # 4. По умолчанию — считаем что найден (если нет явных признаков обратного)
        return True, final_url, status
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, url.format(username), e.code
        # Для других ошибок (403, 500 и т.д.) — не блокируем результат
        return True, url.format(username), e.code
    except urllib.error.URLError:
        # Сетевая ошибка — не блокируем результат
        return True, url.format(username), "network_error"
    except Exception:
        # Другая ошибка — не блокируем результат
        return True, url.format(username), "error"


# ============================================================
# Async-версия (aiohttp) — для ускорения в 10-50x
# ============================================================

try:
    import aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False


async def _check_site_async(site_name, session, url_template, username, not_found_patterns, semaphore):
    """Асинхронная проверка одного сайта.
    
    Возвращает кортеж: (site_name, is_found, final_url, status)
    """
    async with semaphore:
        check_url = url_template.format(username)
        
        try:
            async with session.get(
                check_url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ssl=ctx,
                allow_redirects=True,
                headers={"User-Agent": USER_AGENT}
            ) as resp:
                html = await resp.text(encoding="utf-8", errors="ignore")
                final_url = str(resp.url)
                status = resp.status
                
                # 1. Приоритет: HTTP 404 = уверенно NOT FOUND
                if status == 404:
                    return (site_name, False, check_url, status)
                
                # 2. Основной анализ: позитивные + негативные маркеры
                score = _score_profile(html, username, check_url, final_url, site_name)
                if score == 1:
                    return (site_name, True, final_url, status)
                if score == -1:
                    return (site_name, False, check_url, status)
                
                # 3. Fallback: старые паттерны в полном HTML
                if not_found_patterns:
                    html_lower = html.lower()
                    for pattern in not_found_patterns:
                        if pattern.lower() in html_lower:
                            return (site_name, False, check_url, status)
                
                # 4. По умолчанию — считаем что найден
                return (site_name, True, final_url, status)
                
        except asyncio.TimeoutError:
            return (site_name, False, check_url, "timeout")
        except aiohttp.ClientConnectorSSLError:
            return (site_name, False, check_url, "ssl_error")
        except aiohttp.ClientError as e:
            # Для других ошибок (403, 500 и т.д.) — не блокируем результат
            return (site_name, True, check_url, str(e))
        except Exception:
            # Другая ошибка — не блокируем результат
            return (site_name, True, check_url, "error")


async def quick_search_async(username):
    """Асинхронный быстрый поиск по никнейму — все сайты проверяются параллельно."""
    global SITE_CHECKS
    
    if not _HAS_AIOHTTP:
        # Fallback на синхронную версию если aiohttp не установлен
        print_warning("aiohttp не установлен. Используйте: pip install aiohttp")
        print_warning("Переход к синхронному поиску...\n")
        return await quick_search_sync_fallback(username)
    
    total = len(SITE_CHECKS)
    results = []
    found = 0
    errors = 0
    completed = 0
    
    # Создаём семафор для ограничения параллелизма
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    
    # Создаём общий aiohttp-сессию (connection pooling)
    connector = aiohttp.TCPConnector(
        ssl=ctx,
        limit=MAX_CONCURRENCY,
        limit_per_host=MAX_CONCURRENCY,
        enable_cleanup_closed=True,
    )
    
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT}
    ) as session:
        
        # Создаём задачи для всех сайтов
        tasks = []
        for site_name, site_info in SITE_CHECKS.items():
            not_found_patterns = site_info.get("not_found", [])
            task = _check_site_async(
                site_name,
                session,
                site_info["url"],
                username,
                not_found_patterns,
                semaphore
            )
            tasks.append(task)
        
        # Запускаем задачи через as_completed — результаты приходят по мере готовности
        async for result in asyncio.as_completed(tasks):
            site_name, is_found, final_url, status = await result
            completed += 1
            
            # Обновляем прогресс-бар
            if is_found:
                found += 1
                results.append((site_name, final_url, "Найден"))
                # Выводим найденный сразу
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                               f'\033[92m[+]\033[0m {site_name:18s} → {final_url}')
                sys.stdout.flush()
            else:
                results.append((site_name, final_url, f"HTTP {status}" if isinstance(status, int) else status))
                if status in ("network_error", "error", "timeout", "ssl_error"):
                    errors += 1
                # Показываем прогресс без найденных
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                               f'\033[90m{site_name:18s}\033[0m')
                sys.stdout.flush()
    
    print()  # новая строка после прогресса
    return results, found, errors, total


async def quick_search_sync_fallback(username):
    """Синхронный fallback — если aiohttp недоступен."""
    results = []
    found = 0
    errors = 0
    total = len(SITE_CHECKS)
    
    for i, (site_name, site_info) in enumerate(SITE_CHECKS.items(), 1):
        check_url_str = site_info["url"].format(username)
        
        sys.stdout.write(f'\r  [{i}/{total}] {site_name:15s} ...')
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
    
    return results, found, errors, total


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
    # --- Discord (сторонние каталоги) ---
    "Disboard": {
        "url": "https://disboard.org/search?q={}",
        "not_found": ["not found"],
    },
    "DiscordMe": {
        "url": "https://discord.me/{}",
        "not_found": ["not found", "404"],
    },
    "TopGG": {
        "url": "https://top.gg/search?q={}",
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
    """Быстрый поиск по никнейму — использует asyncio + aiohttp для параллельной проверки."""
    print_info(f"Быстрый поиск по никнейму: {username}\n")
    print_info(f"Проверка {len(SITE_CHECKS)} сайтов (async, concurrency={MAX_CONCURRENCY})...\n")
    
    # Запускаем async-поиск с общим таймаутом
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        try:
            results, found, errors, total = loop.run_until_complete(
                asyncio.wait_for(quick_search_async(username), timeout=TOTAL_TIMEOUT)
            )
        except asyncio.TimeoutError:
            print_error(f"\n  Поиск превысил лимит {TOTAL_TIMEOUT} секунд. Отменяю...")
            # Отменяем все оставшиеся задачи
            for task in asyncio.all_tasks(loop):
                task.cancel()
            try:
                loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(), return_exceptions=True))
            except Exception:
                pass
            return
        
    except KeyboardInterrupt:
        print("\n  Остановлено пользователем.")
        for task in asyncio.all_tasks(loop):
            task.cancel()
        try:
            loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(), return_exceptions=True))
        except Exception:
            pass
        return
    finally:
        loop.close()
    
    # Вывод результатов
    clear_screen()
    print_banner()
    print(f"\n  === Результаты поиска: {username} ===\n")
    print(f"  Найдено: {found}/{total}  |  Ошибок: {errors}\n")
    
    # Сортируем результаты: сначала найденные (по алфавиту), потом не найденные (по алфавиту)
    found_results = sorted(
        [(s, u, st) for s, u, st in results if st == "Найден"],
        key=lambda x: x[0].lower()
    )
    not_found_results = sorted(
        [(s, u, st) for s, u, st in results if st != "Найден"],
        key=lambda x: x[0].lower()
    )
    
    if found_results:
        print("  \033[92mНайдены:\033[0m")
        for site, url, status in found_results:
            print(f"  \033[92m[+]\033[0m  {site:18s} → {url}")
        
        print()
    
    if not_found_results:
        print("  \033[91mНе найдены:\033[0m")
        for site, url, status in not_found_results:
            print(f"  \033[91m[-]\033[0m  {site:18s} → {url}")
    elif not found_results:
        print("  Аккаунты не найдены на проверенных сайтах.")
    
    # Сохраняем результат (также сортируем)
    output_text = f"Поиск: {username}\nНайдено: {found}/{total}\nОшибок: {errors}\n\n"
    for site, url, status in found_results + not_found_results:
        marker = "[+]" if status == "Найден" else "[-]"
        output_text += f"{marker} {site:18s} → {url}\n"
    
    filepath = save_output(f"osint_{sanitize_filename(username)}.txt", output_text)
    print_info(f"Результат сохранён в: {filepath}")
    
    if safe_input("\n  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Quick search completed for: {username}, found: {found}, errors: {errors}")
