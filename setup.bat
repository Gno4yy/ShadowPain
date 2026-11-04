@echo off
chcp 65001 >nul
title ShadowPain Auto Setup
cls

echo.
echo ShadowPain Dashboard - Auto Setup
echo =================================
echo.
echo This will install:
echo   - Python 3.12+ (if not installed)
echo   - pip packages (sqlmap, requests, PySocks, etc.)
echo   - Hashcat (portable)
echo   - Git (if not installed)
echo.
echo Requires internet connection.
echo.
set /p confirm="Continue? (y/n): "
if /i not "%confirm%"=="y" (
    echo Cancelled.
    pause
    exit /b
)

echo.
echo =================================
echo Step 1/4: Check Python
echo =================================

python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is already installed
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
    echo        Version: %PYTHON_VERSION%
) else (
    echo [!] Python not found. Installing...
    echo Downloading Python...
    set PYTHON_INSTALLER=%TEMP%\python-installer.exe
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile '%PYTHON_INSTALLER%'"
    if exist "%PYTHON_INSTALLER%" (
        echo Installing Python silently...
        start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1
        del /f /q "%PYTHON_INSTALLER%"
        if %errorlevel% equ 0 (
            echo [OK] Python installed
            set PYTHON_DIR=%USERPROFILE%\Python312
            set PATH=%PYTHON_DIR%;%PYTHON_DIR%\Scripts;%PATH%
        ) else (
            echo [!] Auto install failed.
            echo Install Python manually: https://python.org
            echo IMPORTANT: Check "Add Python to PATH"
        )
    ) else (
        echo [!] Cannot download Python.
        echo Install manually: https://python.org/downloads
        echo IMPORTANT: Check "Add Python to PATH"
    )
)

echo.
echo =================================
echo Step 2/4: Install pip packages
echo =================================

echo Upgrading pip...
python -m pip install --upgrade pip --quiet 2>nul

echo Installing packages...
python -m pip install requests PySocks prettytable tldextract colorama --quiet
if %errorlevel% equ 0 (
    echo [OK] Main packages installed
)

echo Installing Sherlock...
python -m pip install sherlock-project --quiet 2>nul
if %errorlevel% equ 0 (
    echo [OK] Sherlock installed
) else (
    echo [!] Sherlock failed (will use quick_search)
)

echo Installing sqlmap...
python -m pip install sqlmap --quiet 2>nul
if %errorlevel% equ 0 (
    echo [OK] sqlmap installed
) else (
    echo [!] sqlmap failed
)

echo.
echo =================================
echo Step 3/4: Hashcat
echo =================================

set HASHCAT_DIR=%~dp0portable\hashcat
if exist "%HASHCAT_DIR%\hashcat.exe" (
    echo [OK] Hashcat already installed
) else (
    echo Downloading Hashcat...
    mkdir "%HASHCAT_DIR%" 2>nul
    set HASHCAT_URL=https://github.com/hashcat/hashcat/releases/download/v6.6.2/hashcat-6.6.2.7z
    set HASHCAT_7Z=%TEMP%\hashcat.7z
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/hashcat/hashcat/releases/download/v6.6.2/hashcat-6.6.2.7z' -OutFile '%HASHCAT_7Z%'"
    if exist "%HASHCAT_7Z%" (
        echo Extracting...
        if exist "%~dp0portable\7z.exe" (
            "%~dp0portable\7z.exe" x "%HASHCAT_7Z%" -o"%HASHCAT_DIR%" -y >nul
        ) else (
            echo [!] 7-Zip not found. Download Hashcat manually:
            echo     https://hashcat.net/hashcat/
            echo     Extract to portable/hashcat/
        )
        del /f /q "%HASHCAT_7Z%"
        echo [OK] Hashcat extracted
    ) else (
        echo [!] Cannot download Hashcat.
    )
)

echo.
echo =================================
echo Step 4/4: Git
echo =================================

git --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Git is already installed
) else (
    echo [!] Git not found.
    echo Install: https://git-scm.com/download/win
)

echo.
echo =================================
echo Generating launcher
echo =================================

echo Creating ShadowPain.bat...
(
echo @echo off
echo chcp 65001 ^>nul
echo title ShadowPain Dashboard
echo cls
echo.
echo python main.py
echo pause
) > ShadowPain.bat

echo [OK] ShadowPain.bat created

echo.
echo =================================
echo Setup Complete!
echo =================================
echo.
echo Installed:
echo   [OK] Python %PYTHON_VERSION%
echo   [OK] pip packages
echo   [OK] sqlmap, Sherlock
echo   [!] Hashcat - download from hashcat.net
echo   [!] Wireshark - download from wireshark.org
echo   [!] Tor Browser - download from torproject.org
echo.
echo Run: ShadowPain.bat
echo Or:  python main.py
echo.
pause
