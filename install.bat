@echo off
chcp 65001 >nul
title MIYA v8.0 - Install

:: ============================================================
::  MIYA v8.0 - 依赖安装
::  
::  install.bat             完整安装
::  install.bat dev         开发环境
::  install.bat minimal     最小安装
::  install.bat lightweight 轻量级 (Mock模式)
::  install.bat check       仅检查依赖
::  install.bat upgrade     升级全部依赖
:: ============================================================

:: check python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo   MIYA v8.0 - Installing Dependencies
echo ================================================================================
echo.

if /i "%1"=="dev" (
    echo [1/2] Install core dependencies...
    pip install -r requirements.txt
    echo [2/2] Install dev tools...
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

:: default: full install
pip install -r requirements.txt

:done
echo.
echo ================================================================================
echo   Verify installation...
echo ================================================================================
python setup\scripts\verify_install.py

:end
echo.
echo Done! Run start.bat to launch MIYA.
pause
