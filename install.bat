@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title MIYA v8.0 - Install

:: ============================================================
::  MIYA v8.0 - 依赖安装 (pip / uv 双模式)
::  
::  install.bat             完整安装 (pip)
::  install.bat dev         开发环境 (pip)
::  install.bat minimal     最小安装 (pip)
::  install.bat lightweight 轻量级 (pip)
::  install.bat check       仅检查依赖
::  install.bat upgrade     升级全部依赖 (pip)
::
::  install.bat uv          使用 uv 完整安装
::  install.bat uv dev      使用 uv 开发环境
::  install.bat uv minimal  使用 uv 最小安装
::  install.bat uv lightweight  使用 uv 轻量级
::  install.bat uv sync     仅同步 uv.lock
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

if /i "%1"=="dev" (
    pip install -r requirements.txt
    pip install -r setup\dependencies\dev.txt
    goto :done
)

if /i "%1"=="minimal" (
    pip install -r setup\requirements\minimal.txt
    goto :done
)

if /i "%1"=="lightweight" (
    pip install -r setup\requirements\lightweight.txt
    goto :done
)

if /i "%1"=="check" (
    python setup\scripts\check_deps.py
    goto :end
)

if /i "%1"=="upgrade" (
    pip install -r requirements.txt --upgrade
    goto :done
)

pip install -r requirements.txt
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
echo ================================================================================
echo   Verify installation...
echo ================================================================================
python setup\scripts\verify_install.py 2>nul || echo [WARN] verify_install.py not found, skipping...

:end
echo.
echo Done! Run start.bat to launch MIYA.
pause

:refresh_path
endlocal & set "PATH=%USERPROFILE%\.local\bin;%PATH%"
setlocal
goto :eof
