@echo off
set PYTHONPATH=%~dp0portable\lib
set PATH=%~dp0portable\Lib;%PATH%
python main.py
pause
