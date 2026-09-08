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

set "DAEMON_CMD=set PYTHONIOENCODING=utf-8 && chcp 65001 >nul && uv run python -X utf8 run/daemon.py --api-port 9800"
set "MIYA_ROOT=%CD%"

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

echo Starting MIYA Terminal...
set PYTHONIOENCODING=utf-8 && chcp 65001 >nul && uv run python -X utf8 run/main.py
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
%DAEMON_CMD%
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

:: 2026-09 修复：项目路径含 '#' 时 Vite 必然构建失败
:: （Vite 把路径中 '#' 之后的内容当作 URL 锚点截断），切换到无#目录联接启动
call :ensure_nohash
cd /d "%NOHASH_CD%"
if exist "miya_frontend\dist-electron\main.js" del /q "miya_frontend\dist-electron\main.js"

echo Starting Electron desktop app...
echo   后端需单独启动 (start.bat 2)
start "MIYA Desktop" cmd /c "set MIYA_NO_BACKEND=1 && cd miya_frontend && npm run dev"
echo.
echo [OK] Desktop app launched
timeout /t 2 >nul
goto :restart

:: ============================================================
:web
cls
echo.
echo ================================================================================
echo   MIYA Web Frontend (Ops Center)
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

:: 2026-09 修复：路径含 '#' 时 Vite dev server 同样无法工作，切换到无#联接
call :ensure_nohash
cd /d "%NOHASH_CD%"

echo Cleaning up existing Vite instances...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":5173 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   Killed PID %%a on port 5173
)

echo Starting Ops Center on port 5173...
echo.
echo   ➜  http://localhost:5173
echo.
start "MIYA Web" cmd /c "cd frontend\ui && npm run dev"
timeout /t 4 >nul
echo [OK] Ops Center launched
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
start "MIYA Daemon" /B cmd /c "%DAEMON_CMD%"
timeout /t 3 >nul
echo [OK] Daemon started

:: Desktop (background)
if exist "miya_frontend\package.json" (
    echo [2/4] Starting Desktop app...
    call :ensure_nohash
    cd /d "%NOHASH_CD%"
    if exist "miya_frontend\dist-electron\main.js" del /q "miya_frontend\dist-electron\main.js"
    start "MIYA Desktop" /B cmd /c "set MIYA_NO_BACKEND=1 && cd miya_frontend && npm run dev"
    timeout /t 2 >nul
    echo [OK] Desktop launched
) else (
    echo [2/4] Desktop app not found, skipped
)

:: Web (background)
if exist "frontend\ui\package.json" (
    echo [3/4] Starting Ops Center (port 5173)...
    call :ensure_nohash
    cd /d "%NOHASH_CD%"
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":5173 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
    start "MIYA Web" /B cmd /c "cd frontend\ui && npm run dev"
    timeout /t 3 >nul
    echo [OK] http://localhost:5173
) else (
    echo [3/4] Web frontend not found, skipped
)

:: Terminal (foreground)
echo [4/4] Starting Terminal (foreground)...
echo.

:: 2026-09 修复：claude-code-engine 未安装时回退到内置终端模式（原命令必然 MODULE_NOT_FOUND）
if exist "claude-code-engine\dist\cli-node.js" (
    start "MIYA Terminal" wt node claude-code-engine\dist\cli-node.js
) else (
    echo   [WARN] claude-code-engine 未安装，终端以内置模式（run/main.py）回退
    start "MIYA Terminal" wt uv run python -X utf8 run/main.py
)
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

:: ============================================================
:: 确保在不含 '#' 的工作目录下启动 Node/Vite 工具链
:: （Vite 的 cleanUrl 把路径中 '#' 之后的内容当 URL 锚点截断，
::   导致 "Could not resolve ..."、EISDIR 与渲染层白屏）
:: 方案：subst 盘符映射（Node 的 fs.realpathSync 对 subst 不穿透，
::   配合 scripts/patch_vite_realpath.mjs 替换 vite 的 native realpath）
:: 输入: MIYA_ROOT  输出: NOHASH_CD
:: ============================================================
:ensure_nohash
set "NOHASH_CD=%MIYA_ROOT%"
echo %MIYA_ROOT%| findstr /C:"#" >nul
if errorlevel 1 goto :eof

:: 检查是否已有指向本项目的 subst 映射可复用
for %%L in (Z Y X W V U T S) do (
    subst %%L: >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=2 delims=: " %%P in ('subst %%L:') do (
            if /i "%%P"=="%MIYA_ROOT%" set "SUBST_DRIVE=%%L:"
        )
    )
)
if defined SUBST_DRIVE (
    echo [FIX] 复用已有盘符映射 %SUBST_DRIVE% -^> %MIYA_ROOT%
    set "NOHASH_CD=%SUBST_DRIVE%\"
    goto :eof
)

:: 从 Z 往下找空闲盘符
set "SUBST_DRIVE="
for %%L in (Z Y X W V U T S R) do (
    if not defined SUBST_DRIVE (
        subst %%L: >nul 2>&1
        if errorlevel 1 set "SUBST_DRIVE=%%L:"
    )
)
if not defined SUBST_DRIVE (
    echo [ERROR] 无空闲盘符可用，Electron/Web 模式可能无法启动
    goto :eof
)
subst %SUBST_DRIVE% "%MIYA_ROOT%" >nul 2>&1
if not exist "%SUBST_DRIVE%\start.bat" (
    echo [ERROR] subst 盘符映射创建失败，Electron/Web 模式可能无法启动
    goto :eof
)
echo [FIX] 项目路径含 '#'，已通过盘符映射启动: %SUBST_DRIVE%\ -^> %MIYA_ROOT%
set "NOHASH_CD=%SUBST_DRIVE%\"
goto :eof
