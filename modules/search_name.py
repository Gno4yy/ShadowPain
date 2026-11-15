"""
Search by Name Module
"""

import re
import urllib.request
import ssl
import urllib.parse

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def normalize_name(name):
    """Нормализация ФИО"""
    name = name.strip()
    # Убираем лишние пробелы
    name = re.sub(r'\s+', ' ', name)
    return name


def search_by_name():
    """Поиск по ФИО и дате рождения"""
    from utils.helpers import clear_screen, print_banner, print_info, print_success, print_warning, print_error, save_output, safe_input
    
    clear_screen()
    print_banner()
    print("  === Поиск по ФИО и дате рождения ===\n")
    
    # Ввод данных
    fullname = input("  Введите ФИО (Фамилия Имя Отчество): ").strip()
    if not fullname:
        print_error("ФИО не может быть пустым!")
        if safe_input("  [Enter для продолжения...]") is None:
            import sys
            sys.exit(0)
        return
    
    birth_date = input("  Введите дату рождения (ДД.ММ.ГГГГ, необязательно): ").strip()
    
    # Нормализация
    fullname = normalize_name(fullname)
    parts = fullname.split()
    surname = parts[0] if len(parts) > 0 else ""
    firstname = parts[1] if len(parts) > 1 else ""
    middlename = parts[2] if len(parts) > 2 else ""
    
    print_info(f"\nПоиск: {fullname}")
    if birth_date:
        print_info(f"Дата рождения: {birth_date}")
    
    results = []
    
    # 1. Поиск в Google
    print_info("\n1. Поиск в Google...")
    queries = [
        fullname,
        f"{surname} {firstname}",
        f"{surname} {firstname} {middlename}",
    ]
    if birth_date:
        queries.append(f"{fullname} {birth_date}")
    
    for query in queries:
        encoded = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded}"
        results.append({"engine": "Google", "query": query, "url": url})
        print_info(f"  [{query}] -> {url}")
    
    # 2. Поиск в Yandex
    print_info("\n2. Поиск в Yandex...")
    for query in queries:
        encoded = urllib.parse.quote(query)
        url = f"https://yandex.ru/search/?text={encoded}"
        results.append({"engine": "Yandex", "query": query, "url": url})
        print_info(f"  [{query}] -> {url}")
    
    # 3. Поиск в социальных сетях
    print_info("\n3. Поиск в социальных сетях...")
    social_searches = [
        ("VK", f"https://vk.com/fixsearch?q={urllib.parse.quote(fullname)}"),
        ("Odnoklassniki", f"https://ok.ru/search/search?search_tgt=users&group_name=0&reinit=false&s_filter={urllib.parse.quote(fullname)}"),
        ("Facebook", f"https://www.facebook.com/search/top?q={urllib.parse.quote(fullname)}"),
    ]
    for service, url in social_searches:
        results.append({"engine": service, "query": fullname, "url": url})
        print_info(f"  [{service}] {url}")
    
    # 4. Поиск по утечкам
    print_info("\n4. Проверка по базам утечек...")
    if fullname:
        # HaveIBeenPwned работает только с email, но можно проверить по nikнейму
        hibe_url = f"https://haveibeenpwned.com/account-search?q={urllib.parse.quote(fullname)}"
        results.append({"engine": "HIBP", "query": fullname, "url": hibe_url})
        print_info(f"  [HaveIBeenPwned] {hibe_url}")
    
    # 5. Поиск в профессиональных сетях
    print_info("\n5. Профессиональные сети...")
    prof_searches = [
        ("LinkedIn", f"https://www.linkedin.com/search/results/all/?keywords={urllib.parse.quote(fullname)}"),
        ("HeadHunter", f"https://hh.ru/search/resume?text={urllib.parse.quote(fullname)}"),
    ]
    for service, url in prof_searches:
        results.append({"engine": service, "query": fullname, "url": url})
        print_info(f"  [{service}] {url}")
    
    # Сохранение результатов
    output = f"Поиск по ФИО: {fullname}\n"
    if birth_date:
        output += f"Дата рождения: {birth_date}\n"
    output += f"\nЗапросы для поиска:\n\n"
    
    for r in results:
        output += f"[{r['engine']}] {r['query']}\n"
        output += f"  {r['url']}\n\n"
    
    filepath = save_output(f"name_{surname}_{firstname}.txt", output)
    print_info(f"\nРезультат сохранён в: {filepath}")
    
    if safe_input("\n  [Enter для продолжения...]") is None:
        import sys
        sys.exit(0)

