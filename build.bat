@echo off
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
title MIYA v8.0 - Build

:: ============================================================
::  MIYA v8.0 - Frontend Build
::
::  build.bat             build all (CCE + Desktop)
::  build.bat cce         CCE terminal only
::  build.bat desktop     Electron desktop app only
:: ============================================================

:: check python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

:: init submodule if needed
if not exist "claude-code-engine\package.json" (
    echo [INFO] Claude Code Engine submodule not initialized, running git submodule update...
    git submodule update --init -- claude-code-engine
    if errorlevel 1 (
        echo [WARN] Failed to init CCE submodule, skipping CCE build
        set CCE_SKIP=1
    )
)
echo.

:: sync frontend config
python scripts\sync_frontend_config.py
echo.

:: check node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found
    pause
    exit /b 1
)

set MODE=%1
if not "%MODE%"=="" goto :start_build

:: no arg — show interactive menu
:show_menu
echo.
echo   ==========================================
echo          MIYA v8.0 - Build Menu
echo   ==========================================
echo     [1] Build All (CCE + Desktop)
echo     [2] Build CCE (Terminal Engine)
echo     [3] Build Desktop (Electron App)
echo     [Q] Quit
echo   ==========================================
echo.
set /p CHOICE="  Select [1/2/3/Q]: "
if /i "%CHOICE%"=="1" set MODE=all
if /i "%CHOICE%"=="2" set MODE=cce
if /i "%CHOICE%"=="3" set MODE=desktop
if /i "%CHOICE%"=="Q" goto :quit
if "%MODE%"=="" (
    echo Invalid choice.
    pause
    goto :show_menu
)
goto :start_build

:quit
exit /b 0

:start_build
echo.
echo Starting build mode: %MODE%
echo.

:: ==================== CCE ====================
if /i "%MODE%"=="cce" goto :build_cce
if /i "%MODE%"=="all" goto :build_cce
goto :check_desktop

:build_cce
echo.
echo ================================================================================
echo   Building Claude Code Engine (CCE)...
echo ================================================================================
echo.

if "%CCE_SKIP%"=="1" (
    echo [SKIP] CCE submodule not available, skipping CCE build
    if /i "%MODE%"=="cce" goto :done
    goto :check_desktop
)

:: check bun (only needed for CCE)
where bun >nul 2>&1
if errorlevel 1 (
    echo [INFO] bun not found, auto-installing...
    call npm install -g bun
    if errorlevel 1 (
        echo [ERROR] Failed to install bun. Please install manually: npm install -g bun
        if /i "%MODE%"=="cce" pause
        if /i "%MODE%"=="cce" exit /b 1
        echo [WARN] Skipping CCE build (bun unavailable)
        goto :check_desktop
    )
    echo [OK] bun installed successfully
)

cd /d "%~dp0claude-code-engine"
echo [INFO] Installing CCE dependencies...
start /wait "" bun install
if errorlevel 1 (
    echo [ERROR] CCE dependency install failed!
    cd /d "%~dp0"
    if /i "%MODE%"=="cce" pause
    if /i "%MODE%"=="cce" exit /b 1
    echo [WARN] Skipping CCE build, continuing with desktop...
    goto :check_desktop
)
echo [INFO] Building CCE...
start /wait "" bun run build
if errorlevel 1 (
    echo [ERROR] CCE build failed!
    cd /d "%~dp0"
    if /i "%MODE%"=="cce" pause
    if /i "%MODE%"=="cce" exit /b 1
    echo [WARN] CCE build failed, continuing with desktop...
    goto :check_desktop
)
cd /d "%~dp0"
echo [OK] CCE build complete
if /i "%MODE%"=="cce" goto :done

:: ==================== Desktop ====================
:check_desktop
if /i "%MODE%"=="desktop" goto :build_desktop
if /i "%MODE%"=="all" goto :build_desktop
goto :done

:build_desktop
echo.
echo ================================================================================
echo   Building Electron Desktop App...
echo ================================================================================
echo.
if exist "miya_frontend\package.json" (
    cd /d "%~dp0miya_frontend"
    echo [INFO] Installing desktop dependencies...
    call npm install --legacy-peer-deps
    if errorlevel 1 (
        echo [ERROR] Desktop dependency install failed!
        cd /d "%~dp0"
        goto :done
    )
    echo [INFO] Setting up esbuild binary...
    node node_modules\esbuild\install.js 2>nul
    echo [INFO] Building desktop app...
    call npm run build
    if errorlevel 1 (
        echo [ERROR] Desktop build failed!
        cd /d "%~dp0"
        goto :done
    )
    cd /d "%~dp0"
    echo [OK] Desktop build complete
) else (
    echo [WARN] miya_frontend not found, skipping...
)
if /i "%MODE%"=="desktop" goto :done

:done
echo.
echo ================================================================================
echo   Build Complete!
echo ================================================================================
echo.
pause
