@echo off
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

:: sync frontend config
python scripts\sync_frontend_config.py
echo.

:: check bun
where bun >nul 2>&1
if errorlevel 1 (
    echo [ERROR] bun not found. Install: npm install -g bun
    pause
    exit /b 1
)

:: check node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found
    pause
    exit /b 1
)

set MODE=%1
if "%MODE%"=="" set MODE=all

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
cd claude-code-engine
if not exist "node_modules\" (
    echo [INFO] Installing CCE dependencies...
    bun install
)
echo [INFO] Building CCE...
bun run build
if errorlevel 1 (
    echo [ERROR] CCE build failed!
    cd ..
    pause
    exit /b 1
)
cd ..
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
    cd miya_frontend
    if not exist "node_modules\" (
        echo [INFO] Installing desktop dependencies...
        call npm install
    )
    echo [INFO] Building desktop app...
    call npm run build
    if errorlevel 1 (
        echo [ERROR] Desktop build failed!
        cd ..
        pause
        exit /b 1
    )
    cd ..
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
