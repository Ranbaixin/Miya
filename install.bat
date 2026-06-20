@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title MIYA v8.0 - Install

:: ============================================================
::  MIYA v8.0 - Dependency Installer (pip / uv dual mode)
::
::  install.bat             all deps (pip)
::  install.bat dev         all + dev tools (pip)
::  install.bat minimal     minimal (pip)
::  install.bat lightweight lightweight (pip)
::  install.bat check       check only
::  install.bat upgrade     upgrade all (pip)
::
::  install.bat uv          full via uv
::  install.bat uv dev      dev via uv
::  install.bat uv minimal  minimal via uv
::  install.bat uv lightweight lightweight via uv
::  install.bat uv sync     sync uv.lock
:: ============================================================

:: check python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

:: check if first arg is "uv"
if /i "%1"=="uv" (
    shift
    goto :uv_install
)

:: ==================== pip mode ====================
echo.
echo ================================================================================
echo   MIYA v8.0 - Installing Dependencies (pip)
echo ================================================================================
echo.

:: Quick pre-check: skip pip if ALL dependencies already installed
if "%1"=="" (
    python setup\scripts\verify_install.py --all >nul 2>&1
    if not errorlevel 1 (
        echo [OK] All dependencies already installed, skipping...
        goto :end
    )
    echo [INFO] Missing dependencies detected, installing...
    echo.
)

if /i "%1"=="dev" (
    pip install -q -r setup/requirements/full.txt
    pip install -q -r setup/dependencies/dev.txt
    goto :done
)

if /i "%1"=="minimal" (
    pip install -q -r setup\requirements\minimal.txt
    goto :done
)

if /i "%1"=="lightweight" (
    pip install -q -r setup\requirements\lightweight.txt
    goto :done
)

if /i "%1"=="check" (
    python setup\scripts\check_deps.py
    goto :end
)

if /i "%1"=="upgrade" (
    pip install --upgrade -r requirements.txt
    goto :done
)

pip install -q -r requirements.txt
python scripts\sync_frontend_config.py
goto :done

:: ==================== uv mode ====================
:uv_install

where uv >nul 2>&1
if errorlevel 1 (
    echo [INFO] uv not found. Installing uv...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    :: refresh PATH
    call :refresh_path
)

echo.
echo ================================================================================
echo   MIYA v8.0 - Installing Dependencies (uv)
echo ================================================================================
echo.

if /i "%1"=="dev" (
    echo Installing full dependencies + dev tools...
    uv sync --all-extras --group dev
    goto :done
)

if /i "%1"=="minimal" (
    echo Installing minimal dependencies...
    uv sync
    goto :done
)

if /i "%1"=="lightweight" (
    echo Installing lightweight dependencies (AI + base)...
    uv sync --extra ai
    goto :done
)

if /i "%1"=="sync" (
    echo Syncing from uv.lock...
    uv sync --all-extras --group dev --frozen
    goto :done
)

:: default uv install: full
echo Installing full production dependencies...
uv sync --all-extras

:done
echo.
echo Done! Run start.bat to launch MIYA.
pause
goto :eof

:end
pause
goto :eof

:refresh_path
endlocal & set "PATH=%USERPROFILE%\.local\bin;%PATH%"
setlocal
goto :eof
