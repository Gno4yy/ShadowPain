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
from modules.search_name import search_by_name as _search_by_name
from modules.search_ip import search_by_ip as _search_by_ip
from modules.search_id import search_by_unique_id as _search_by_unique_id

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


async def search_email_async(email):
    """Асинхронный поиск по email — все сайты проверяются параллельно."""
    global SITE_CHECKS_EMAIL
    
    if not _HAS_AIOHTTP:
        print_warning("aiohttp не установлен. Используйте: pip install aiohttp")
        print_warning("Переход к синхронному поиску...\n")
        return await search_email_sync_fallback(email)
    
    total = len(SITE_CHECKS_EMAIL)
    results = []
    found = 0
    errors = 0
    completed = 0
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    
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
        
        tasks = []
        for site_name, site_info in SITE_CHECKS_EMAIL.items():
            not_found_patterns = site_info.get("not_found", [])
            task = _check_site_async(
                site_name,
                session,
                site_info["url"],
                email,
                not_found_patterns,
                semaphore
            )
            tasks.append(task)
        
        async for result in asyncio.as_completed(tasks):
            site_name, is_found, final_url, status = await result
            completed += 1
            
            if is_found:
                found += 1
                results.append((site_name, final_url, "Найден"))
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                               f'\033[92m[+]\033[0m {site_name:18s} → {final_url}')
                sys.stdout.flush()
            else:
                results.append((site_name, final_url, f"HTTP {status}" if isinstance(status, int) else status))
                if status in ("network_error", "error", "timeout", "ssl_error"):
                    errors += 1
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                               f'\033[90m{site_name:18s}\033[0m')
                sys.stdout.flush()
    
    print()
    return results, found, errors, total


async def search_email_sync_fallback(email):
    """Синхронный fallback для поиска по email."""
    results = []
    found = 0
    errors = 0
    total = len(SITE_CHECKS_EMAIL)
    
    for i, (site_name, site_info) in enumerate(SITE_CHECKS_EMAIL.items(), 1):
        check_url_str = site_info["url"].format(email)
        
        sys.stdout.write(f'\r  [{i}/{total}] {site_name:15s} ...')
        sys.stdout.flush()
        
        try:
            not_found_patterns = site_info.get("not_found", [])
            is_found, final_url, status = check_site(site_info["url"], email, not_found_patterns)
            
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


async def search_phone_async(phone):
    """Асинхронный поиск по телефону — все сайты проверяются параллельно."""
    global SITE_CHECKS_PHONE
    
    if not _HAS_AIOHTTP:
        print_warning("aiohttp не установлен. Используйте: pip install aiohttp")
        print_warning("Переход к синхронному поиску...\n")
        return await search_phone_sync_fallback(phone)
    
    total = len(SITE_CHECKS_PHONE)
    results = []
    found = 0
    errors = 0
    completed = 0
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    
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
        
        tasks = []
        for site_name, site_info in SITE_CHECKS_PHONE.items():
            not_found_patterns = site_info.get("not_found", [])
            task = _check_site_async(
                site_name,
                session,
                site_info["url"],
                phone,
                not_found_patterns,
                semaphore
            )
            tasks.append(task)
        
        async for result in asyncio.as_completed(tasks):
            site_name, is_found, final_url, status = await result
            completed += 1
            
            if is_found:
                found += 1
                results.append((site_name, final_url, "Найден"))
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                               f'\033[92m[+]\033[0m {site_name:18s} → {final_url}')
                sys.stdout.flush()
            else:
                results.append((site_name, final_url, f"HTTP {status}" if isinstance(status, int) else status))
                if status in ("network_error", "error", "timeout", "ssl_error"):
                    errors += 1
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                               f'\033[90m{site_name:18s}\033[0m')
                sys.stdout.flush()
    
    print()
    return results, found, errors, total


async def search_phone_sync_fallback(phone):
    """Синхронный fallback для поиска по телефону."""
    results = []
    found = 0
    errors = 0
    total = len(SITE_CHECKS_PHONE)
    
    for i, (site_name, site_info) in enumerate(SITE_CHECKS_PHONE.items(), 1):
        check_url_str = site_info["url"].format(phone)
        
        sys.stdout.write(f'\r  [{i}/{total}] {site_name:15s} ...')
        sys.stdout.flush()
        
        try:
            not_found_patterns = site_info.get("not_found", [])
            is_found, final_url, status = check_site(site_info["url"], phone, not_found_patterns)
            
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
        "url": "https://x.com/user/{}",
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

# ============================================================
# Базы сайтов для поиска по EMAIL
# ============================================================
SITE_CHECKS_EMAIL = {
    # --- Социальные сети ---
    "Facebook": {
        "url": "https://www.facebook.com/search/top/?q={}",
        "not_found": ["sorry, this page isn't", "page not found"],
    },
    "Twitter/X": {
        "url": "https://twitter.com/search?q={}&src=typed_query",
        "not_found": [],
    },
    "Instagram": {
        "url": "https://www.instagram.com/search/users/?query={}",
        "not_found": [],
    },
    "VK": {
        "url": "https://vk.com/fixsearch?q={}",
        "not_found": ["страница не найдена", "page not found"],
    },
    "Reddit": {
        "url": "https://www.reddit.com/search/?q={}&type=user",
        "not_found": ["page doesn't exist"],
    },
    "LinkedIn": {
        "url": "https://www.linkedin.com/search/results/all/?keywords={}",
        "not_found": [],
    },
    "Telegram": {
        "url": "https://t.me/search?q={}",
        "not_found": ["not found"],
    },
    # --- Профессиональные ---
    "GitHub": {
        "url": "https://github.com/search?q={}&type=users",
        "not_found": ["there's nothing here"],
    },
    "StackOverflow": {
        "url": "https://stackoverflow.com/users/search?q={}",
        "not_found": [],
    },
    "GitLab": {
        "url": "https://gitlab.com/search?search={}&type=users",
        "not_found": ["not found"],
    },
    "HackerOne": {
        "url": "https://hackerone.com/?q={}",
        "not_found": ["not found"],
    },
    "DevTo": {
        "url": "https://dev.to/search?q={}",
        "not_found": [],
    },
    # --- Блоги и статьи ---
    "Medium": {
        "url": "https://medium.com/search?q={}",
        "not_found": ["not found"],
    },
    "WordPress": {
        "url": "https://{}.wordpress.com",
        "not_found": ["not found", "page not found"],
    },
    "Blogger": {
        "url": "https://{}.blogspot.com",
        "not_found": ["not found"],
    },
    "Tumblr": {
        "url": "https://{}.tumblr.com",
        "not_found": ["not found"],
    },
    # --- Форумы ---
    "XDA": {
        "url": "https://forum.xda-developers.com/members/?username={}",
        "not_found": ["member not found"],
    },
    "IndieHackers": {
        "url": "https://www.indiehackers.com/search?q={}",
        "not_found": [],
    },
    "ProductHunt": {
        "url": "https://www.producthunt.com/search?q={}",
        "not_found": ["not found"],
    },
    # --- Крипто и Web3 ---
    "Ethereum": {
        "url": "https://etherscan.io/address/{}",
        "not_found": [],
    },
    "OpenSea": {
        "url": "https://opensea.io/{}",
        "not_found": ["not found"],
    },
    # --- Игровые платформы ---
    "Steam": {
        "url": "https://steamcommunity.com/search/users?text={}",
        "not_found": [],
    },
    "Roblox": {
        "url": "https://www.roblox.com/search/users?keyword={}",
        "not_found": ["not found"],
    },
    # --- Маркетплейсы ---
    "Etsy": {
        "url": "https://www.etsy.com/search/people?q={}",
        "not_found": [],
    },
    "eBay": {
        "url": "https://www.ebay.com/usr/{}",
        "not_found": ["not found"],
    },
    "Poshmark": {
        "url": "https://poshmark.com/closet/{}",
        "not_found": ["not found"],
    },
    # --- Приватность и безопасность ---
    "HaveIBeenPwned": {
        "url": "https://haveibeenpwned.com/account/{}",
        "not_found": [],
    },
    "HaveIbeenWarner": {
        "url": "https://haveibeenwarned.com/profile/{}",
        "not_found": [],
    },
    # --- Фото и видео ---
    "Flickr": {
        "url": "https://www.flickr.com/people/{}",
        "not_found": ["not found"],
    },
    "500px": {
        "url": "https://500px.com/p/{}",
        "not_found": ["not found"],
    },
    "Vimeo": {
        "url": "https://vimeo.com/{}",
        "not_found": ["not found"],
    },
    "Dailymotion": {
        "url": "https://www.dailymotion.com/search/{}",
        "not_found": [],
    },
    # --- Музыка ---
    "SoundCloud": {
        "url": "https://soundcloud.com/{}",
        "not_found": ["not found"],
    },
    "Bandcamp": {
        "url": "https://bandcamp.com/{}",
        "not_found": ["not found"],
    },
    "Last.fm": {
        "url": "https://www.last.fm/user/{}",
        "not_found": ["not found"],
    },
    # --- Дизайн ---
    "Dribbble": {
        "url": "https://dribbble.com/search/{}",
        "not_found": [],
    },
    "Behance": {
        "url": "https://www.behance.net/search/?search={}",
        "not_found": ["not found"],
    },
    "DeviantArt": {
        "url": "https://www.deviantart.com/{}",
        "not_found": ["not found"],
    },
    # --- Код и разработка ---
    "Replit": {
        "url": "https://replit.com/@{}",
        "not_found": ["not found"],
    },
    "CodePen": {
        "url": "https://codepen.io/{}",
        "not_found": ["not found"],
    },
    "HackerRank": {
        "url": "https://www.hackerrank.com/profile/{}",
        "not_found": ["not found"],
    },
    "LeetCode": {
        "url": "https://leetcode.com/search/?q={}",
        "not_found": [],
    },
    # --- Другие ---
    "About.me": {
        "url": "https://about.me/{}",
        "not_found": ["not found"],
    },
    "Linktree": {
        "url": "https://linktr.ee/{}",
        "not_found": ["not found"],
    },
    "Beacons": {
        "url": "https://beacons.page/{}",
        "not_found": ["not found"],
    },
    "Gravatar": {
        "url": "https://en.gravatar.com/{}",
        "not_found": ["not found"],
    },
    "Keybase": {
        "url": "https://keybase.io/{}",
        "not_found": ["not found"],
    },
    "TikTok": {
        "url": "https://www.tiktok.com/search/?q={}&type=user",
        "not_found": ["not found"],
    },
    "YouTube": {
        "url": "https://www.youtube.com/results?search_query={}&sp=EgIYAQ%253D%253D",
        "not_found": [],
    },
    }

# ============================================================
# Базы сайтов для поиска по ТЕЛЕФОНУ
# ============================================================
SITE_CHECKS_PHONE = {
    # --- Мессенджеры ---
    "Telegram": {
        "url": "https://t.me/{}",
        "not_found": ["not found", "no such channel"],
    },
    "WhatsApp": {
        "url": "https://api.whatsapp.com/send?phone={}",
        "not_found": [],
    },
    "Viber": {
        "url": "https://www.viber.com/contacts/?phone={}",
        "not_found": [],
    },
    "Signal": {
        "url": "https://signal.me/#p/{}",
        "not_found": [],
    },
    "Line": {
        "url": "https://line.me/ti/p/{}",
        "not_found": ["not found"],
    },
    "WeChat": {
        "url": "https://www.wechat.com/search?q={}",
        "not_found": [],
    },
    # --- Социальные сети ---
    "Facebook": {
        "url": "https://www.facebook.com/search/top/?q={}",
        "not_found": ["sorry, this page isn't"],
    },
    "VK": {
        "url": "https://vk.com/fixsearch?q={}",
        "not_found": ["страница не найдена"],
    },
    "Instagram": {
        "url": "https://www.instagram.com/search/users/?q={}",
        "not_found": [],
    },
    "Twitter/X": {
        "url": "https://twitter.com/search?q={}&src=typed_query",
        "not_found": [],
    },
    "TikTok": {
        "url": "https://www.tiktok.com/search/?q={}&type=user",
        "not_found": ["not found"],
    },
    # --- Профили и резюме ---
    "LinkedIn": {
        "url": "https://www.linkedin.com/search/results/all/?keywords={}",
        "not_found": [],
    },
    "HeadHunter": {
        "url": "https://hh.ru/search/resume?text={}",
        "not_found": [],
    },
    # --- Игровые платформы ---
    "Steam": {
        "url": "https://steamcommunity.com/search/users?text={}",
        "not_found": [],
    },
    "Discord": {
        "url": "https://discord.com/search?q={}",
        "not_found": [],
    },
    "PlayStation": {
        "url": "https://psnprofiles.com/search/?searchPlayer={}",
        "not_found": ["not found"],
    },
    "Xbox": {
        "url": "https://xboxgamertag.com/search/{}",
        "not_found": ["not found"],
    },
    # --- Маркетплейсы ---
    "PoshMarket": {
        "url": "https://pos.market/search?q={}",
        "not_found": [],
    },
    "Avito": {
        "url": "https://www.avito.ru/search/users?query={}",
        "not_found": [],
    },
    "Юла": {
        "url": "https://www.yula.ru/people/?q={}",
        "not_found": [],
    },
    # --- Поиск людей ---
    "TruePeople": {
        "url": "https://www.truepeoplesearch.com/results?phonenumber={}",
        "not_found": [],
    },
    "WhitePages": {
        "url": "https://www.whitepages.com/search?query={}",
        "not_found": [],
    },
    "SpyDialer": {
        "url": "https://www.spydialer.com/default.aspx",
        "not_found": [],
    },
    "Phonebook": {
        "url": "https://phonebook.cz/?search={}",
        "not_found": [],
    },
    # --- Российские сервисы ---
    "YouTalk": {
        "url": "https://youtalk.ru/search?q={}",
        "not_found": [],
    },
    "NumBuster": {
        "url": "https://numbuster.com/search?q={}",
        "not_found": [],
    },
    "WhoCalled": {
        "url": "https://whocalled.me/search?q={}",
        "not_found": [],
    },
    # --- Форумы и сообщества ---
    "Reddit": {
        "url": "https://www.reddit.com/search/?q={}&type=user",
        "not_found": ["page doesn't exist"],
    },
    "GitHub": {
        "url": "https://github.com/search?q={}&type=users",
        "not_found": ["there's nothing here"],
    },
    # --- Другие ---
    "Gravatar": {
        "url": "https://en.gravatar.com/site/search/email/hash?query={}",
        "not_found": ["not found"],
    },
    "Keybase": {
        "url": "https://keybase.io/search?q={}",
        "not_found": ["not found"],
    },
    }


def run_osint_module():
    """Модуль OSINT — расширенный поиск по различным данным"""
    while True:
        clear_screen()
        print_banner()
        print("\n  === OSINT: Расширенный поиск ===\n")
        print("  [1]  Поиск по никнейму (соцсети)")
        print("  [2]  Поиск по номеру телефона")
        print("  [3]  Поиск по ФИО и дате рождения")
        print("  [4]  Поиск по email")
        print("  [5]  Поиск по IP-адресу")
        print("  [6]  Поиск по уникальному ID (VK, Telegram, YouTube)")
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
            phone = input("\n  Введите номер телефона (например: +79991234567): ").strip()
            if not phone:
                print_error("Номер телефона не может быть пустым!")
                if safe_input("  [Enter для продолжения...]") is None:
                    sys.exit(0)
                continue
            search_by_phone(phone)
        elif choice == "3":
            _search_by_name()
        elif choice == "4":
            email = input("\n  Введите email: ").strip()
            if not email:
                print_error("Email не может быть пустым!")
                if safe_input("  [Enter для продолжения...]") is None:
                    sys.exit(0)
                continue
            search_by_email(email)
        elif choice == "5":
            ip = input("\n  Введите IP-адрес: ").strip()
            if not ip:
                print_error("IP-адрес не может быть пустым!")
                if safe_input("  [Enter для продолжения...]") is None:
                    sys.exit(0)
                continue
            _search_by_ip(ip)
        elif choice == "6":
            _search_by_unique_id()
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

# ============================================================
# Поиск по EMAIL — POST-запросы к формам регистрации/восстановления
# ============================================================

SITE_CHECKS_EMAIL_AUTH = {
    "Facebook": {
    "url": "https://www.facebook.com/recover/initiate",
    "method": "POST",
    "fields": {"ident": "{}"},
    "sent_patterns": ["code sent", "verification code", "check your email", "your code is"],
    "not_found": ["enter your email"],
    },
    "Instagram": {
    "url": "https://www.instagram.com/accounts/account_recovery_send/",
    "method": "POST",
    "fields": {"email": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": [],
    },
    "VK": {
    "url": "https://vk.com/recover.php",
    "method": "POST",
    "fields": {"email": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": ["enter your email"],
    },
    "Reddit": {
    "url": "https://www.reddit.com/api/recovery",
    "method": "POST",
    "fields": {"user": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": [],
    },
    "LinkedIn": {
    "url": "https://www.linkedin.com/authguard/password-reset/send-email",
    "method": "POST",
    "fields": {"session_redirect": "https://www.linkedin.com/password-reset", "email_address": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": [],
    },
    "GitHub": {
    "url": "https://github.com/password_reset",
    "method": "GET",
    "fields": {},
    "sent_patterns": [],
    "not_found": [],
    "note": "requires CSRF token from GET request",
    },
    "StackOverflow": {
    "url": "https://stackoverflow.com/users/authenticated-password-reset",
    "method": "POST",
    "fields": {"email": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": [],
    },
    "Steam": {
    "url": "https://store.steampowered.com/password/reset",
    "method": "POST",
    "fields": {"fieldname": "emailaddress", "email_to_use": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": [],
    },
    "eBay": {
    "url": "https://www.ebay.com/signin/srvr",
    "method": "POST",
    "fields": {"email": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": [],
    },
    "WordPress": {
    "url": "https://wordpress.com/wp-login.php?action=lostpassword",
    "method": "POST",
    "fields": {"user_login": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": [],
    },
    "TikTok": {
    "url": "https://www.tiktok.com/passport/email/forgot-password/",
    "method": "POST",
    "fields": {"email": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": [],
    },
    "Medium": {
    "url": "https://medium.com/m/signin",
    "method": "GET",
    "fields": {},
    "sent_patterns": [],
    "not_found": [],
    },
    "YouTube": {
    "url": "https://accounts.google.com/signin/v2/challenge/password",
    "method": "GET",
    "fields": {},
    "sent_patterns": [],
    "not_found": [],
    },
    }

# ============================================================
# Поиск по ТЕЛЕФОНУ — POST-запросы к формам регистрации/восстановления
# ============================================================

SITE_CHECKS_PHONE_AUTH = {
    "Telegram": {
    "url": "https://my.telegram.org/auth",
    "method": "POST",
    "fields": {"phone": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": ["enter your phone"],
    },
    "WhatsApp": {
    "url": "https://web.whatsapp.com/",
    "method": "GET",
    "fields": {},
    "sent_patterns": [],
    "not_found": [],
    "note": "requires QR code scan",
    },
    "Viber": {
    "url": "https://www.viber.com/contacts/",
    "method": "GET",
    "fields": {},
    "sent_patterns": [],
    "not_found": [],
    },
    "Signal": {
    "url": "https://signal.me/#p/",
    "method": "GET",
    "fields": {},
    "sent_patterns": [],
    "not_found": [],
    },
    "Facebook": {
    "url": "https://www.facebook.com/recover/initiate",
    "method": "POST",
    "fields": {"ident": "{}"},
    "sent_patterns": ["code sent", "verification code", "check your phone"],
    "not_found": ["enter your email"],
    },
    "Twitter/X": {
    "url": "https://twitter.com/i/api/mm/auth/password/initiate.json",
    "method": "POST",
    "fields": {"phone_number": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "Instagram": {
    "url": "https://www.instagram.com/accounts/account_recovery_send/",
    "method": "POST",
    "fields": {"phone": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "VK": {
    "url": "https://vk.com/recover.php",
    "method": "POST",
    "fields": {"phone": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": ["enter your phone"],
    },
    "TikTok": {
    "url": "https://www.tiktok.com/passport/phone/forgot-password/",
    "method": "POST",
    "fields": {"phone": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "Steam": {
    "url": "https://store.steampowered.com/password/reset",
    "method": "POST",
    "fields": {"fieldname": "phone", "phone_number": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "PlayStation": {
    "url": "https://id.sonyentertainmentnetwork.com/signin/#/reset-password",
    "method": "POST",
    "fields": {"loginpin": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "Xbox": {
    "url": "https://account.xbox.com/auth/resetpassword",
    "method": "POST",
    "fields": {"username": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "eBay": {
    "url": "https://www.ebay.com/signin/srvr",
    "method": "POST",
    "fields": {"phone": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "Avito": {
    "url": "https://www.avito.ru/password_recover",
    "method": "POST",
    "fields": {"phone": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "Mail.ru": {
    "url": "https://account.mail.ru/signup",
    "method": "POST",
    "fields": {"primary_password": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "Yandex": {
    "url": "https://passport.yandex.com/rest_registration/password-reset.json",
    "method": "POST",
    "fields": {"login": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "LinkedIn": {
    "url": "https://www.linkedin.com/authguard/password-reset/send-email",
    "method": "POST",
    "fields": {"session_redirect": "https://www.linkedin.com/password-reset", "phone_number": "{}"},
    "sent_patterns": ["code sent", "verification", "check your phone"],
    "not_found": [],
    },
    "Discord": {
    "url": "https://discord.com/api/v9/auth/reset-password",
    "method": "POST",
    "fields": {"email": "{}"},
    "sent_patterns": ["code sent", "verification", "check your email"],
    "not_found": [],
    },
    }


async def _check_auth_site_async(site_name, session, site_info, value, sent_patterns, not_found_patterns, semaphore):
    """Асинхронная проверка сайта через POST/GET-запрос к форме регистрации/восстановления"""
    async with semaphore:
        check_url = site_info["url"].format(value)
        
        try:
            # Формируем данные для отправки
            data = {}
            for field_name, field_template in site_info.get("fields", {}).items():
                data[field_name] = field_template.format(value)
            
            if site_info.get("method") == "POST":
                async with session.post(
                    check_url,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    ssl=ctx,
                    allow_redirects=True,
                    headers={"User-Agent": USER_AGENT}
                ) as resp:
                    html = await resp.text(encoding="utf-8", errors="ignore")
                    final_url = str(resp.url)
                    status = resp.status
                    
                    # Проверяем, отправил ли сайт код
                    html_lower = html.lower()
                    for pattern in sent_patterns:
                        if pattern.lower() in html_lower:
                            return (site_name, True, final_url, status)
                    
                    # Проверяем, не ошибка ли это
                    for pattern in not_found_patterns:
                        if pattern.lower() in html_lower:
                            return (site_name, False, final_url, status)
                    
                    # Если нет явных признаков - считаем что не найдено
                    return (site_name, False, final_url, status)
            else:
                # GET запрос
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
                    
                    html_lower = html.lower()
                    for pattern in sent_patterns:
                        if pattern.lower() in html_lower:
                            return (site_name, True, final_url, status)
                    
                    for pattern in not_found_patterns:
                        if pattern.lower() in html_lower:
                            return (site_name, False, final_url, status)
                    
                    return (site_name, False, final_url, status)
                    
        except asyncio.TimeoutError:
            return (site_name, False, check_url, "timeout")
        except aiohttp.ClientConnectorSSLError:
            return (site_name, False, check_url, "ssl_error")
        except aiohttp.ClientError as e:
            return (site_name, False, check_url, str(e))
        except Exception:
            return (site_name, False, check_url, "error")




async def search_email_auth_async(email):
    """Асинхронный поиск по email через POST-запросы к формам регистрации"""
    global SITE_CHECKS_EMAIL_AUTH
    
    if not _HAS_AIOHTTP:
        print_warning("aiohttp не установлен. Используйте: pip install aiohttp")
        print_warning("Переход к синхронному поиску...\n")
        return await search_email_auth_sync_fallback(email)
    
    total = len(SITE_CHECKS_EMAIL_AUTH)
    results = []
    found = 0
    errors = 0
    completed = 0
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    
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
        
        tasks = []
        for site_name, site_info in SITE_CHECKS_EMAIL_AUTH.items():
            task = _check_auth_site_async(
                site_name,
                session,
                site_info,
                email,
                site_info["sent_patterns"],
                site_info["not_found"],
                semaphore
            )
            tasks.append(task)
        
        async for result in asyncio.as_completed(tasks):
            site_name, is_found, final_url, status = await result
            completed += 1
            
            if is_found:
                found += 1
                results.append((site_name, final_url, "Код отправлен"))
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                            f'\033[92m[+]\033[0m {site_name:18s} \u2192 {final_url}')
                sys.stdout.flush()
            else:
                results.append((site_name, final_url, f"HTTP {status}" if isinstance(status, int) else status))
                if status in ("network_error", "error", "timeout", "ssl_error"):
                    errors += 1
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                            f'\033[90m{site_name:18s}\033[0m')
                sys.stdout.flush()
    
    print()
    return results, found, errors, total


async def search_phone_auth_async(phone):
    """Асинхронный поиск по телефону через POST-запросы к формам регистрации"""
    global SITE_CHECKS_PHONE_AUTH

    if not _HAS_AIOHTTP:
        print_warning("aiohttp не установлен. Используйте: pip install aiohttp")
        print_warning("Переход к синхронному поиску...\n")
        return await search_phone_auth_sync_fallback(phone)

    total = len(SITE_CHECKS_PHONE_AUTH)
    results = []
    found = 0
    errors = 0
    completed = 0

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

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

        tasks = []
        for site_name, site_info in SITE_CHECKS_PHONE_AUTH.items():
            task = _check_auth_site_async(
                site_name,
                session,
                site_info,
                phone,
                site_info["sent_patterns"],
                site_info["not_found"],
                semaphore
            )
            tasks.append(task)

        async for result in asyncio.as_completed(tasks):
            site_name, is_found, final_url, status = await result
            completed += 1

            if is_found:
                found += 1
                results.append((site_name, final_url, "Код отправлен"))
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                               f'\033[92m[+]\033[0m {site_name:18s} \u2192 {final_url}')
                sys.stdout.flush()
            else:
                results.append((site_name, final_url, f"HTTP {status}" if isinstance(status, int) else status))
                if status in ("network_error", "error", "timeout", "ssl_error"):
                    errors += 1
                sys.stdout.write(f'\r  [\033[92m{found}\033[0m/{total}] {completed}/{total}  '
                               f'\033[90m{site_name:18s}\033[0m')
                sys.stdout.flush()

    print()
    return results, found, errors, total


async def search_phone_auth_sync_fallback(phone):
    """Синхронный fallback для поиска по телефону."""
    results = []
    found = 0
    errors = 0
    total = len(SITE_CHECKS_PHONE_AUTH)

    for i, (site_name, site_info) in enumerate(SITE_CHECKS_PHONE_AUTH.items(), 1):
        check_url_str = site_info["url"]
        sys.stdout.write(f'\r  [{i}/{total}] {site_name:15s} ...')
        sys.stdout.flush()
        try:
            data = {}
            for field_name, field_template in site_info.get("fields", {}).items():
                data[field_name] = field_template.format(phone)

            if site_info.get("method") == "POST":
                req = urllib.request.Request(
                    check_url_str,
                    data=json.dumps(data).encode("utf-8"),
                    headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"}
                )
                resp = urllib.request.urlopen(req, timeout=10, context=ctx)
                html = resp.read().decode("utf-8", errors="ignore")
                final_url = resp.geturl()
                status = resp.status
            else:
                req = urllib.request.Request(check_url_str, headers={"User-Agent": USER_AGENT})
                resp = urllib.request.urlopen(req, timeout=10, context=ctx)
                html = resp.read().decode("utf-8", errors="ignore")
                final_url = resp.geturl()
                status = resp.status

            html_lower = html.lower()
            is_found = False
            for pattern in site_info["sent_patterns"]:
                if pattern.lower() in html_lower:
                    is_found = True
                    break

            for pattern in site_info.get("not_found", []):
                if pattern.lower() in html_lower:
                    is_found = False
                    break

            if is_found:
                results.append((site_name, final_url, "Код отправлен"))
                found += 1
            else:
                results.append((site_name, final_url, f"HTTP {status}" if isinstance(status, int) else status))
                if status in ("network_error", "error", "timeout", "ssl_error"):
                    errors += 1
        except Exception:
            results.append((site_name, check_url_str, "Ошибка"))
            errors += 1

    return results, found, errors, total


async def search_email_auth_sync_fallback(email):
    """Синхронный fallback для поиска по email."""
    results = []
    found = 0
    errors = 0
    total = len(SITE_CHECKS_EMAIL_AUTH)

    for i, (site_name, site_info) in enumerate(SITE_CHECKS_EMAIL_AUTH.items(), 1):
        check_url_str = site_info["url"]

        sys.stdout.write(f'\r  [{i}/{total}] {site_name:15s} ...')
        sys.stdout.flush()

        try:
            data = {}
            for field_name, field_template in site_info.get("fields", {}).items():
                data[field_name] = field_template.format(email)

            if site_info.get("method") == "POST":
                req = urllib.request.Request(
                    check_url_str,
                    data=json.dumps(data).encode("utf-8"),
                    headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"}
                )
                resp = urllib.request.urlopen(req, timeout=10, context=ctx)
                html = resp.read().decode("utf-8", errors="ignore")
                final_url = resp.geturl()
                status = resp.status
            else:
                req = urllib.request.Request(check_url_str, headers={"User-Agent": USER_AGENT})
                resp = urllib.request.urlopen(req, timeout=10, context=ctx)
                html = resp.read().decode("utf-8", errors="ignore")
                final_url = resp.geturl()
                status = resp.status

            html_lower = html.lower()
            is_found = False
            for pattern in site_info["sent_patterns"]:
                if pattern.lower() in html_lower:
                    is_found = True
                    break

            for pattern in site_info.get("not_found", []):
                if pattern.lower() in html_lower:
                    is_found = False
                    break

            if is_found:
                results.append((site_name, final_url, "Код отправлен"))
                found += 1
            else:
                results.append((site_name, final_url, f"HTTP {status}" if isinstance(status, int) else status))
                if status in ("network_error", "error", "timeout", "ssl_error"):
                    errors += 1
        except Exception:
            results.append((site_name, check_url_str, "Ошибка"))
            errors += 1

    return results, found, errors, total

def search_by_email(email):
    """Поиск по email — POST-запросы к формам регистрации/восстановления"""
    print_info(f"Поиск аккаунтов по email: {email}")
    print_info(f"Проверка {len(SITE_CHECKS_EMAIL_AUTH)} сайтов (auth-based, concurrency={MAX_CONCURRENCY})...\n")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        try:
            results, found, errors, total = loop.run_until_complete(
                asyncio.wait_for(search_email_auth_async(email), timeout=TOTAL_TIMEOUT)
            )
        except asyncio.TimeoutError:
            print_error(f"\n  Поиск превысил лимит {TOTAL_TIMEOUT} секунд. Отменяю...")
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
    print(f"\n  === Результаты поиска: {email} ===\n")
    print(f"  Найдено: {found}/{total}  |  Ошибок: {errors}\n")

    found_results = sorted(
        [(s, u, st) for s, u, st in results if st == "Код отправлен"],
        key=lambda x: x[0].lower()
    )
    not_found_results = sorted(
        [(s, u, st) for s, u, st in results if st != "Код отправлен"],
        key=lambda x: x[0].lower()
    )

    if found_results:
        print("  \033[92mEmail найден (код подтверждения отправлен):\033[0m")
        for site, url, status in found_results:
            print(f"  \033[92m[+]\033[0m  {site:18s} → {url}")
        print()

    if not_found_results:
        print("  \033[91mНе найден:\033[0m")
        for site, url, status in not_found_results:
            print(f"  \033[91m[-]\033[0m  {site:18s} → {url}")
    elif not found_results:
        print("  Email не найден на проверенных сайтах.")

    # Сохраняем результат
    output_text = f"Поиск по email: {email}\nНайдено: {found}/{total}\nОшибок: {errors}\n\n"
    for site, url, status in found_results + not_found_results:
        marker = "[+]" if status == "Код отправлен" else "[-]"
        output_text += f"{marker} {site:18s} → {url}\n"

    filepath = save_output(f"osint_email_{sanitize_filename(email)}.txt", output_text)
    print_info(f"Результат сохранён в: {filepath}")

    if safe_input("\n  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Email search completed for: {email}, found: {found}, errors: {errors}")


def search_by_phone(phone):
    """Поиск по телефону — POST-запросы к формам регистрации/восстановления"""
    print_info(f"Поиск аккаунтов по телефону: {phone}")
    print_info(f"Проверка {len(SITE_CHECKS_PHONE_AUTH)} сайтов (auth-based, concurrency={MAX_CONCURRENCY})...\n")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        try:
            results, found, errors, total = loop.run_until_complete(
                asyncio.wait_for(search_phone_auth_async(phone), timeout=TOTAL_TIMEOUT)
            )
        except asyncio.TimeoutError:
            print_error(f"\n  Поиск превысил лимит {TOTAL_TIMEOUT} секунд. Отменяю...")
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
    print(f"\n  === Результаты поиска: {phone} ===\n")
    print(f"  Найдено: {found}/{total}  |  Ошибок: {errors}\n")

    found_results = sorted(
        [(s, u, st) for s, u, st in results if st == "Код отправлен"],
        key=lambda x: x[0].lower()
    )
    not_found_results = sorted(
        [(s, u, st) for s, u, st in results if st != "Код отправлен"],
        key=lambda x: x[0].lower()
    )

    if found_results:
        print("  \033[92mТелефон найден (код подтверждения отправлен):\033[0m")
        for site, url, status in found_results:
            print(f"  \033[92m[+]\033[0m  {site:18s} → {url}")
        print()

    if not_found_results:
        print("  \033[91mНе найден:\033[0m")
        for site, url, status in not_found_results:
            print(f"  \033[91m[-]\033[0m  {site:18s} → {url}")
    elif not found_results:
        print("  Телефон не найден на проверенных сайтах.")

    # Сохраняем результат
    output_text = f"Поиск по телефону: {phone}\nНайдено: {found}/{total}\nОшибок: {errors}\n\n"
    for site, url, status in found_results + not_found_results:
        marker = "[+]" if status == "Код отправлен" else "[-]"
        output_text += f"{marker} {site:18s} → {url}\n"

    filepath = save_output(f"osint_phone_{sanitize_filename(phone)}.txt", output_text)
    print_info(f"Результат сохранён в: {filepath}")

    if safe_input("\n  [Enter для продолжения...]") is None:
        sys.exit(0)
    logger.info(f"Phone search completed for: {phone}, found: {found}, errors: {errors}")


