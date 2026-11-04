@echo off
chcp 65001 >nul
title ShadowPain — Автоматическая установка
color 0A
cls

echo.
echo   ============================================
echo    ShadowPain Dashboard — Автоустановка
echo   ============================================
echo.
echo  Этот скрипт установит:
echo    - Python 3.12+ (если не установлен)
echo    - pip-пакеты (sqlmap, requests, PySocks и др.)
echo    - Hashcat (portable)
echo    - Wireshark/tshark (portable)
echo    - Tor Browser (portable)
echo    - Git (если не установлен)
echo.
echo  Требуется подключение к интернету.
echo  Запуск от имени администратора не обязателен.
echo.
set /p confirm="  Продолжить? (y/n): "
if /i not "%confirm%"=="y" (
    echo.
    echo  Отменено.
    pause
    exit /b
)

echo.
echo  ============================================
echo   Шаг 1/6: Проверка Python
echo  ============================================

python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Python уже установлен
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
    echo         Версия: %PYTHON_VERSION%
) else (
    echo  [!] Python не найден. Установка...
    
    echo  Скачивание Python...
    set PYTHON_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe
    set PYTHON_INSTALLER=%TEMP%\python-installer.exe
    
    powershell -Command "(New-Object Net.WebClient).DownloadFile('%PYTHON_URL%', '%PYTHON_INSTALLER%')"
    
    if exist "%PYTHON_INSTALLER%" (
        echo  Установка Python (тихо, в %USERPROFILE%\Python312)...
        start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1
        del /f /q "%PYTHON_INSTALLER%"
        
        if %errorlevel% equ 0 (
            echo  [OK] Python установлен
            set PYTHON_DIR=%USERPROFILE%\Python312
            set PATH=%PYTHON_DIR%;%PYTHON_DIR%\Scripts;%PATH%
        ) else (
            echo  [!] Автоматическая установка не удалась.
            echo      Установите Python вручную: https://python.org
            echo.
            echo      Обязательно отметьте: Add Python to PATH
        )
    ) else (
        echo  [!] Не удалось скачать Python.
        echo      Установите вручную: https://python.org/downloads
        echo      Обязательно отметьте: Add Python to PATH
    )
)

echo.
echo  ============================================
echo   Шаг 2/6: Установка pip-пакетов
echo  ============================================

echo  Обновление pip...
python -m pip install --upgrade pip --quiet 2>nul

echo  Установка основных пакетов...
python -m pip install requests PySocks prettytable tldextract colorama --quiet
if %errorlevel% equ 0 (
    echo  [OK] Основные пакеты установлены
)

echo  Установка Sherlock (OSINT)...
python -m pip install sherlock-project --quiet 2>nul
if %errorlevel% equ 0 (
    echo  [OK] Sherlock установлен
) else (
    echo  [!] Sherlock — ошибка (не критично, будет quick_search)
)

echo  Установка sqlmap...
python -m pip install sqlmap --quiet 2>nul
if %errorlevel% equ 0 (
    echo  [OK] sqlmap установлен
) else (
    echo  [!] sqlmap — ошибка
)

echo.
echo  ============================================
echo   Шаг 3/6: Hashcat (взлом хешей)
echo  ============================================

set HASHCAT_DIR=%~dp0portable\hashcat
if exist "%HASHCAT_DIR%\hashcat.exe" (
    echo  [OK] Hashcat уже установлен
) else (
    echo  Скачивание Hashcat...
    mkdir "%HASHCAT_DIR%" 2>nul
    
    set HASHCAT_URL=https://github.com/hashcat/hashcat/releases/download/v6.6.2/hashcat-6.6.2.7z
    set HASHCAT_7Z=%TEMP%\hashcat.7z
    
    powershell -Command "(New-Object Net.WebClient).DownloadFile('%HASHCAT_URL%', '%HASHCAT_7Z%')"
    
    if exist "%HASHCAT_7Z%" (
        echo  Распаковка...
        if exist "%~dp0portable\7z.exe" (
            "%~dp0portable\7z.exe" x "%HASHCAT_7Z%" -o"%HASHCAT_DIR%" -y >nul
        ) else (
            echo  [!] 7-Zip не найден. Скачайте Hashcat вручную:
            echo      https://hashcat.net/hashcat/
            echo      Распакуйте в portable/hashcat/
        )
        del /f /q "%HASHCAT_7Z%"
        echo  [OK] Hashcat распакован
    ) else (
        echo  [!] Не удалось скачать Hashcat.
    )
)

echo.
echo  ============================================
echo   Шаг 4/6: Wireshark/tshark (анализ трафика)
echo  ============================================

set WIRESHARK_DIR=%~dp0portable\wireshark
if exist "%WIRESHARK_DIR%\tshark.exe" (
    echo  [OK] tshark уже установлен
) else (
    echo  Wireshark не имеет portable-версии.
    echo  Установите вручную: https://www.wireshark.org/download.html
    echo  Или используйте WSL: wsl sudo apt install tshark
)

echo.
echo  ============================================
echo   Шаг 5/6: Tor Browser (анонимность)
echo  ============================================

set TOR_DIR=%~dp0portable\tor
if exist "%TOR_DIR%\Tor Browser\Start Tor Browser.exe" (
    echo  [OK] Tor Browser уже установлен
) else (
    echo  Tor Browser весит ~80MB. Скачайте вручную:
    echo  https://www.torproject.org/download/
    echo  Распакуйте в portable/tor/
)

echo.
echo  ============================================
echo   Шаг 6/6: Git (если не установлен)
echo  ============================================

git --version >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Git уже установлен
) else (
    echo  [!] Git не найден.
    echo      Установите: https://git-scm.com/download/win
)

echo.
echo  ============================================
echo   Генерация скриптов запуска
echo  ============================================

echo  Создаю ShadowPain.bat...
(
echo @echo off
echo chcp 65001 ^>nul
echo title ShadowPain Dashboard
echo cls
echo.
echo   ============================================
echo    ShadowPain Dashboard
echo   ============================================
echo.
echo python main.py
echo pause
) > ShadowPain.bat

echo  [OK] ShadowPain.bat создан

echo.
echo  ============================================
echo   Установка завершена!
echo  ============================================
echo.
echo  Что установлено:
echo    [OK] Python %PYTHON_VERSION%
echo    [OK] pip-пакеты (requests, PySocks, sqlmap, sherlock)
echo    [!] Hashcat — скачайте portable с hashcat.net
echo    [!] Wireshark — установите с wireshark.org
echo    [!] Tor Browser — скачайте с torproject.org
echo.
echo  Запуск: двойной клик ShadowPain.bat
echo  Или: python main.py
echo.
pause
