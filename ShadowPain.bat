@echo off
chcp 65001 >nul
title ShadowPain Dashboard

set PYTHON_CMD=

:: Get actual username
set ACTUAL_USER=
for /f "tokens=2 delims=\" %%u in ('whoami /user /fo list 2^>nul') do set ACTUAL_USER=%%u
if "%ACTUAL_USER%"=="" set ACTUAL_USER=hecke

:: Search ALL Users folders for python3*.exe
for /d %%d in ("%SYSTEMDRIVE%\Users\*") do (
    if exist "%%d\.local\bin\python3*.exe" (
        for /f "delims=" %%f in ('dir /b /a "%%d\.local\bin\python3*.exe" 2^>nul') do if not defined PYTHON_CMD set PYTHON_CMD=%%d\.local\bin\%%f
    )
)

:: Fallback: common Python locations
if "%PYTHON_CMD%"=="" if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" set PYTHON_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe
if "%PYTHON_CMD%"=="" if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" set PYTHON_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe
if "%PYTHON_CMD%"=="" if exist "%PROGRAMFILES%\Python312\python.exe" set PYTHON_CMD=%PROGRAMFILES%\Python312\python.exe
if "%PYTHON_CMD%"=="" if exist "%PROGRAMFILES%\Python311\python.exe" set PYTHON_CMD=%PROGRAMFILES%\Python311\python.exe
if "%PYTHON_CMD%"=="" where python >nul 2>&1 set PYTHON_CMD=python

if "%PYTHON_CMD%"=="" (
    echo ERROR: Python not found!
    echo Install from: https://python.org
    pause
    exit /b 1
)

echo ShadowPain Dashboard
echo ====================
echo Using: %PYTHON_CMD%
echo.
%PYTHON_CMD% main.py

pause
