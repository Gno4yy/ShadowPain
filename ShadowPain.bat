@echo off
chcp 65001 >nul
title ShadowPain Dashboard

set PYTHON_CMD=

:: Find python3*.exe in .local\bin (uv install)
for /f "delims=" %%f in ('dir /b /a "%USERPROFILE%\.local\bin\python3*.exe" 2^>nul') do set PYTHON_CMD=%USERPROFILE%\.local\bin\%%f

:: Fallback: PATH
if "%PYTHON_CMD%"=="" where python >nul 2>&1 set PYTHON_CMD=python

:: Fallback: other locations
if "%PYTHON_CMD%"=="" if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" set PYTHON_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe
if "%PYTHON_CMD%"=="" if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" set PYTHON_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe
if "%PYTHON_CMD%"=="" if exist "%USERPROFILE%\AppData\Local\Python\pythoncore-3.12\python.exe" set PYTHON_CMD=%USERPROFILE%\AppData\Local\Python\pythoncore-3.12\python.exe
if "%PYTHON_CMD%"=="" if exist "%PROGRAMFILES%\Python312\python.exe" set PYTHON_CMD=%PROGRAMFILES%\Python312\python.exe
if "%PYTHON_CMD%"=="" if exist "%PROGRAMFILES%\Python311\python.exe" set PYTHON_CMD=%PROGRAMFILES%\Python311\python.exe

if "%PYTHON_CMD%"=="" (
    echo.
    echo ERROR: Python not found!
    echo.
    echo Python is installed at:
    echo   %USERPROFILE%\.local\bin\python3.15.exe
    echo.
    echo Add to PATH or run:
    echo   "%USERPROFILE%\.local\bin\python3.15.exe" main.py
    echo.
    pause
    exit /b 1
)

echo ShadowPain Dashboard
echo ====================
echo Using: %PYTHON_CMD%
echo.
%PYTHON_CMD% main.py

pause
