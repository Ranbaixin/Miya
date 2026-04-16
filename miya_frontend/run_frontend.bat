@echo off
setlocal

cd /d "%~dp0"
set PYTHONPATH=%~dp0;%~dp0..

python main.py

endlocal