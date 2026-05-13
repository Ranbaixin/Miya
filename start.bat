@echo off
chcp 65001 >nul
title MIYA v8.0

:: ============================================================
::  MIYA v8.0 - Launch Center
::  
::  start.bat           Show menu
::  start.bat 1|2|3|4   Direct launch
::  start.bat a         Launch all
:: ============================================================

:: CLI direct
if /i "%1"=="1" goto :terminal
if /i "%1"=="t" goto :terminal
if /i "%1"=="2" goto :daemon
if /i "%1"=="d" goto :daemon
if /i "%1"=="3" goto :desktop
if /i "%1"=="4" goto :web
if /i "%1"=="a" goto :all

:menu
cls
echo.
echo ================================================================================
echo                         MIYA v8.0  Launch Center
echo ================================================================================
echo.
echo   [1] Terminal    Claude Code + DeepSeek V4
echo   [2] Daemon      Backend (core + platforms + API :9800)
echo   [3] Desktop     Electron desktop app
echo   [4] Web         Browser frontend
echo.
echo   [A] All         Start everything
echo   [0] Exit
echo.
echo ================================================================================
echo.

set /p "choice=Enter choice: "

if "%choice%"=="0" goto :exit
if "%choice%"=="1" goto :terminal
if /i "%choice%"=="t" goto :terminal
if "%choice%"=="2" goto :daemon
if /i "%choice%"=="d" goto :daemon
if "%choice%"=="3" goto :desktop
if "%choice%"=="4" goto :web
if /i "%choice%"=="a" goto :all

echo [ERROR] Invalid choice
timeout /t 1 >nul
goto :menu

:: ============================================================
:terminal
cls
echo.
echo ================================================================================
echo   MIYA Terminal
echo ================================================================================
echo.

if not exist "claude-code-engine\dist\cli-node.js" (
    echo [ERROR] Claude Code Engine not found
    echo Run: cd claude-code-engine ^&^& bun run build:miya
    pause
    goto :menu
)

echo Starting MIYA Terminal...
start "MIYA Terminal" wt node claude-code-engine\dist\cli-node.js
timeout /t 2 >nul
echo.
echo [OK] Terminal session ended
goto :restart

:: ============================================================
:daemon
cls
echo.
echo ================================================================================
echo   MIYA Daemon
echo ================================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    goto :menu
)

echo Starting MIYA Daemon (API on port 9800)...
echo Press Ctrl+C to stop.
echo.
python run/daemon.py --api-port 9800
echo.
echo [OK] Daemon stopped
goto :restart

:: ============================================================
:desktop
cls
echo.
echo ================================================================================
echo   MIYA Desktop (Electron)
echo ================================================================================
echo.

if not exist "miya_frontend\package.json" (
    echo [ERROR] miya_frontend not found
    pause
    goto :menu
)

if not exist "miya_frontend\node_modules\" (
    echo [WARN] Dependencies not installed, running npm install...
    cd miya_frontend
    call npm install
    cd ..
)

echo Starting Electron desktop app...
start "MIYA Desktop" cmd /c "cd miya_frontend && npm run dev"
echo.
echo [OK] Desktop app launched
timeout /t 2 >nul
goto :restart

:: ============================================================
:web
cls
echo.
echo ================================================================================
echo   MIYA Web Frontend
echo ================================================================================
echo.

if not exist "frontend\ui\package.json" (
    echo [ERROR] frontend/ui not found
    pause
    goto :menu
)

if not exist "frontend\ui\node_modules\" (
    echo [WARN] Dependencies not installed, running npm install...
    cd frontend\ui
    call npm install
    cd ..\..
)

echo Starting web frontend...
start "MIYA Web" cmd /c "cd frontend\ui && npm run dev"
echo.
echo [OK] Web frontend launched
timeout /t 2 >nul
goto :restart

:: ============================================================
:all
cls
echo.
echo ================================================================================
echo   MIYA All-in-One
echo ================================================================================
echo.

:: Daemon (background)
echo [1/4] Starting Daemon (background)...
start "MIYA Daemon" /B cmd /c "python run/daemon.py --api-port 9800"
timeout /t 3 >nul
echo [OK] Daemon started

:: Desktop (background)
if exist "miya_frontend\package.json" (
    echo [2/4] Starting Desktop app...
    start "MIYA Desktop" /B cmd /c "cd miya_frontend && npm run dev"
    timeout /t 2 >nul
    echo [OK] Desktop launched
) else (
    echo [2/4] Desktop app not found, skipped
)

:: Web (background)
if exist "frontend\ui\package.json" (
    echo [3/4] Starting Web frontend...
    start "MIYA Web" /B cmd /c "cd frontend\ui && npm run dev"
    timeout /t 2 >nul
    echo [OK] Web launched
) else (
    echo [3/4] Web frontend not found, skipped
)

:: Terminal (foreground)
echo [4/4] Starting Terminal (foreground)...
echo.

start "MIYA Terminal" wt node claude-code-engine\dist\cli-node.js
timeout /t 2 >nul

echo.
echo [OK] All-in-One session ended
echo (Close Daemon/Desktop/Web windows with Ctrl+C)
goto :restart

:: ============================================================
:exit
cls
echo.
echo ================================================================================
echo   Goodbye!
echo ================================================================================
timeout /t 1 >nul
exit /b 0

:: ============================================================
:restart
echo.
echo ================================================================================
set /p "rp=Return to menu? (Y/N): "
if /i "%rp%"=="y" goto :menu
echo Goodbye!
timeout /t 1 >nul
exit /b 0
