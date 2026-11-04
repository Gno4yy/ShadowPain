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

set PYTHON_FOUND=0
set PYTHON_EXE=

:: Try python in PATH
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_FOUND=1
    set PYTHON_EXE=python
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
    echo [OK] Python is already installed
    echo        Version: %PYTHON_VERSION%
)

:: Try common Python locations
if %PYTHON_FOUND% equ 0 (
    if exist "%USERPROFILE%\Python312\python.exe" (
        set PYTHON_FOUND=1
        set PYTHON_EXE=%USERPROFILE%\Python312\python.exe
        set PYTHON_DIR=%USERPROFILE%\Python312
        echo [OK] Found Python at %PYTHON_DIR%
    )
)
if %PYTHON_FOUND% equ 0 (
    if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
        set PYTHON_FOUND=1
        set PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe
        set PYTHON_DIR=%USERPROFILE%\AppData\Local\Programs\Python\Python312
        echo [OK] Found Python at %PYTHON_DIR%
    )
)
if %PYTHON_FOUND% equ 0 (
    if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
        set PYTHON_FOUND=1
        set PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe
        set PYTHON_DIR=%USERPROFILE%\AppData\Local\Programs\Python\Python311
        echo [OK] Found Python at %PYTHON_DIR%
    )
)
if %PYTHON_FOUND% equ 0 (
    if exist "%PROGRAMFILES%\Python312\python.exe" (
        set PYTHON_FOUND=1
        set PYTHON_EXE=%PROGRAMFILES%\Python312\python.exe
        set PYTHON_DIR=%PROGRAMFILES%\Python312
        echo [OK] Found Python at %PYTHON_DIR%
    )
)
if %PYTHON_FOUND% equ 0 (
    if exist "%PROGRAMFILES%\Python311\python.exe" (
        set PYTHON_FOUND=1
        set PYTHON_EXE=%PROGRAMFILES%\Python311\python.exe
        set PYTHON_DIR=%PROGRAMFILES%\Python311
        echo [OK] Found Python at %PYTHON_DIR%
    )
)

if %PYTHON_FOUND% equ 0 (
    echo [!] Python not found. Installing...
    echo Downloading Python...
    set PYTHON_INSTALLER=%TEMP%\python-installer.exe
    
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile '%PYTHON_INSTALLER%'"
    
    if exist "%PYTHON_INSTALLER%" (
        echo Installing Python silently...
        start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1
        del /f /q "%PYTHON_INSTALLER%"
        if %errorlevel% equ 0 (
            set PYTHON_FOUND=1
            set PYTHON_DIR=%USERPROFILE%\Python312
            set PYTHON_EXE=%USERPROFILE%\Python312\python.exe
            echo [OK] Python installed
            echo [!] IMPORTANT: You must restart this script or open a NEW terminal for PATH changes to apply.
            echo     The installed Python is at: %PYTHON_DIR%\python.exe
            echo     Add it to PATH manually or run this script again in a new terminal.
        ) else (
            echo [!] Auto install failed.
            echo Install Python manually: https://python.org
            echo IMPORTANT: Check "Add Python to PATH"
            echo.
            pause
            exit /b 1
        )
    ) else (
        echo [!] Cannot download Python.
        echo Install manually: https://python.org/downloads
        echo IMPORTANT: Check "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
)

echo.
echo =================================
echo Step 2/4: Install pip packages
echo =================================

if "%PYTHON_EXE%"=="python" (
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
) else (
    echo Using Python: %PYTHON_EXE%
    echo Upgrading pip...
    "%PYTHON_EXE%" -m pip install --upgrade pip --quiet 2>nul
    
    echo Installing packages...
    "%PYTHON_EXE%" -m pip install requests PySocks prettytable tldextract colorama --quiet
    if %errorlevel% equ 0 (
        echo [OK] Main packages installed
    )
    
    echo Installing Sherlock...
    "%PYTHON_EXE%" -m pip install sherlock-project --quiet 2>nul
    if %errorlevel% equ 0 (
        echo [OK] Sherlock installed
    ) else (
        echo [!] Sherlock failed (will use quick_search)
    )
    
    echo Installing sqlmap...
    "%PYTHON_EXE%" -m pip install sqlmap --quiet 2>nul
    if %errorlevel% equ 0 (
        echo [OK] sqlmap installed
    ) else (
        echo [!] sqlmap failed
    )
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
echo Step 4/4: Generate launcher
echo =================================

echo Creating ShadowPain.bat...
(
echo @echo off
echo chcp 65001 ^>nul
echo title ShadowPain Dashboard
echo.
echo set PYTHON_CMD=
echo if not "%%PYTHON_CMD%%"=="%%" where python ^>nul 2^>^&1 set PYTHON_CMD=python
echo if not "%%PYTHON_CMD%%"=="%%" if exist "%%USERPROFILE%%\Python312\python.exe" set PYTHON_CMD=%%USERPROFILE%%\Python312\python.exe
echo if not "%%PYTHON_CMD%%"=="%%" if exist "%%USERPROFILE%%\AppData\Local\Programs\Python\Python312\python.exe" set PYTHON_CMD=%%USERPROFILE%%\AppData\Local\Programs\Python\Python312\python.exe
echo if not "%%PYTHON_CMD%%"=="%%" if exist "%%USERPROFILE%%\AppData\Local\Programs\Python\Python311\python.exe" set PYTHON_CMD=%%USERPROFILE%%\AppData\Local\Programs\Python\Python311\python.exe
echo if not "%%PYTHON_CMD%%"=="%%" if exist "%%PROGRAMFILES%%\Python312\python.exe" set PYTHON_CMD=%%PROGRAMFILES%%\Python312\python.exe
echo if not "%%PYTHON_CMD%%"=="%%" if exist "%%PROGRAMFILES%%\Python311\python.exe" set PYTHON_CMD=%%PROGRAMFILES%%\Python311\python.exe
echo if not "%%PYTHON_CMD%%"=="%%" if exist "%%PROGRAMFILES%%\Python310\python.exe" set PYTHON_CMD=%%PROGRAMFILES%%\Python310\python.exe
echo if not "%%PYTHON_CMD%%"=="%%" if exist "%%PROGRAMFILES(x86)%%\Python312\python.exe" set PYTHON_CMD=%%PROGRAMFILES(x86)%%\Python312\python.exe
echo if not "%%PYTHON_CMD%%"=="%%" if exist "%%PROGRAMFILES(x86)%%\Python311\python.exe" set PYTHON_CMD=%%PROGRAMFILES(x86)%%\Python311\python.exe
echo if not "%%PYTHON_CMD%%"=="%%" if exist "%%PROGRAMFILES(x86)%%\Python310\python.exe" set PYTHON_CMD=%%PROGRAMFILES(x86)%%\Python310\python.exe
echo.
echo if "%%PYTHON_CMD%%"=="%%" (
echo     echo.
echo     echo ERROR: Python not found!
echo     echo.
echo     echo Please install Python from: https://python.org
echo     echo IMPORTANT: Check "Add Python to PATH" during installation
echo     echo.
echo     pause
echo     exit /b 1
echo )
echo.
echo ShadowPain Dashboard
echo ====================
echo.
echo %%PYTHON_CMD%% main.py
echo.
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
