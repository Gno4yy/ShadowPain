"""
Search by IP Module
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


def validate_ip(ip):
    """Валидация IP адреса"""
    # IPv4
    pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    match = re.match(pattern, ip)
    if match:
        return all(0 <= int(group) <= 255 for group in match.groups())
    
    # IPv6 (упрощённая проверка)
    if ':' in ip:
        return True
    
    return False


def get_ip_geolocation(ip):
    """Получение геолокации IP через бесплатные API"""
    results = {}
    
    # 1. ip-api.com (бесплатный, без API ключа)
    try:
        url = f"http://ip-api.com/json/{ip}?fields=query,city,regionName,country,isp,org,as,lat,lon,timezone"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        if resp.status == 200:
            data = json.loads(resp.read().decode())
            if data.get("status") == "success":
                results["ip-api.com"] = {
                    "ip": data.get("query"),
                    "city": data.get("city"),
                    "region": data.get("regionName"),
                    "country": data.get("country"),
                    "country_code": data.get("countryCode"),
                    "isp": data.get("isp"),
                    "org": data.get("org"),
                    "as": data.get("as"),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "timezone": data.get("timezone"),
                }
    except Exception as e:
        pass
    
    # 2. ipapi.co (бесплатный)
    try:
        url = f"https://ipapi.co/{ip}/json/"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        if resp.status == 200:
            data = json.loads(resp.read().decode())
            if "error" not in data:
                results["ipapi.co"] = {
                    "ip": data.get("ip"),
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country_name"),
                    "country_code": data.get("country_code"),
                    "isp": data.get("org"),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                    "timezone": data.get("timezone"),
                    "postal": data.get("postal"),
                    "asn": data.get("asn"),
                }
    except Exception:
        pass
    
    # 3. ipinfo.io (бесплатный без ключа с ограничениями)
    try:
        url = f"https://ipinfo.io/{ip}/json"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        if resp.status == 200:
            data = json.loads(resp.read().decode())
            if "ip" in data:
                results["ipinfo.io"] = {
                    "ip": data.get("ip"),
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country"),
                    "loc": data.get("loc"),  # latitude,longitude
                    "org": data.get("org"),
                    "timezone": data.get("timezone"),
                    "postal": data.get("postal"),
                }
    except Exception:
        pass
    
    return results


def check_ip_blacklist(ip):
    """Проверка IP в чёрных списках"""
    results = []
    
    # Основные блеклисты
    blacklists = [
        ("Spamhaus", f"http://www.spamhaus.org/checkip.ashx?ip={ip}"),
        ("Barracuda", f"https://barracudacentral.org/lookups/check1.php?ip={ip}"),
    ]
    
    for name, url in blacklists:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            data = resp.read().decode()
            if "0." in data or "not blacklisted" in data.lower():
                results.append({"list": name, "blacklisted": False})
            else:
                results.append({"list": name, "blacklisted": True})
        except Exception:
            results.append({"list": name, "blacklisted": None, "error": "Проверка невозможна"})
    
    return results


def search_by_ip(ip):
    """Поиск по IP-адресу"""
    from utils.helpers import clear_screen, print_banner, print_info, print_success, print_warning, print_error, save_output, safe_input
    
    clear_screen()
    print_banner()
    print(f"\n  === Поиск по IP: {ip} ===\n")
    
    # Валидация
    if not validate_ip(ip):
        print_error("Неверный формат IP адреса!")
        print_info("Примеры: 8.8.8.8 (IPv4) или 2001:4860:4860::8888 (IPv6)")
        if safe_input("\n  [Enter для продолжения...]") is None:
            import sys
            sys.exit(0)
        return
    
    # 1. Геолокация
    print_info("Получение геолокации...\n")
    geo_data = get_ip_geolocation(ip)
    
    if geo_data:
        print_success("  Данные геолокации:\n")
        for source, data in geo_data.items():
            print_info(f"  --- {source} ---")
            print_success(f"    IP: {data.get('ip', 'N/A')}")
            print_success(f"    Страна: {data.get('country', 'N/A')}")
            print_success(f"    Город: {data.get('city', 'N/A')}")
            print_success(f"    Регион: {data.get('region', 'N/A')}")
            print_success(f"    Провайдер: {data.get('isp', 'N/A')}")
            print_success(f"    ASN: {data.get('as', data.get('org', 'N/A'))}")
            
            lat = data.get('lat', data.get('latitude', data.get('loc', '').split(',')[0]))
            lon = data.get('lon', data.get('longitude', data.get('loc', '').split(',')[1] if ',' in data.get('loc', '') else ''))
            if lat and lon:
                print_success(f"    Координаты: {lat}, {lon}")
                print_info(f"    Карта: https://www.google.com/maps?q={lat},{lon}")
            print()
    else:
        print_warning("  Не удалось получить данные геолокации")
    
    # 2. Проверка блеклистов
    print_info("Проверка в чёрных списках...\n")
    blacklist = check_ip_blacklist(ip)
    
    found_blacklisted = False
    for check in blacklist:
        if check["blacklisted"] is True:
            print_error(f"  [-] {check['list']}: IP в чёрном списке!")
            found_blacklisted = True
        elif check["blacklisted"] is False:
            print_success(f"  [+] {check['list']}: IP не в чёрном списке")
        else:
            print_warning(f"  [?] {check['list']}: {check.get('error', 'Не удалось проверить')}")
    
    if not found_blacklisted:
        print_success("  IP не найден в проверенных чёрных списках")
    
    # 3. Дополнительные ресурсы
    print_info("\nДополнительные ресурсы:\n")
    resources = [
        ("Shodan", f"https://www.shodan.io/host/{ip}"),
        ("Censys", f"https://search.censys.io/hosts/{ip}"),
        ("VirusTotal", f"https://www.virustotal.com/gui/search/{urllib.parse.quote(ip)}"),
        ("Whois", f"https://www.whois.com/whois/{ip}"),
        ("IP2Location", f"https://www.ip2location.com/demo/{ip}"),
        ("MaxMind", f"https://www.maxmind.com/en/ipgeolookup?address={ip}"),
    ]
    for service, url in resources:
        print_info(f"  [{service}] {url}")
    
    # Сохранение результатов
    output = f"Поиск по IP: {ip}\n\n"
    output += "Геолокация:\n"
    for source, data in geo_data.items():
        output += f"\n  --- {source} ---\n"
        output += f"  IP: {data.get('ip', 'N/A')}\n"
        output += f"  Страна: {data.get('country', 'N/A')}\n"
        output += f"  Город: {data.get('city', 'N/A')}\n"
        output += f"  Регион: {data.get('region', 'N/A')}\n"
        output += f"  Провайдер: {data.get('isp', 'N/A')}\n"
        output += f"  ASN: {data.get('as', data.get('org', 'N/A'))}\n"
    
    output += "\nЧёрные списки:\n"
    for check in blacklist:
        status = "BLACKLISTED" if check["blacklisted"] else "CLEAN" if check["blacklisted"] is False else "ERROR"
        output += f"  {check['list']}: {status}\n"
    
    filepath = save_output(f"ip_{ip.replace('.', '_')}.txt", output)
    print_info(f"\nРезультат сохранён в: {filepath}")
    
    if safe_input("\n  [Enter для продолжения...]") is None:
        import sys
        sys.exit(0)

