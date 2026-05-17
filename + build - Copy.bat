@echo off
title PSO2NGS LCT - Build

echo ============================================
echo  PSO2NGS LCT - Build Script
echo ============================================
echo.

echo [1/2] Checking Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [1/2] Installing
pyinstaller PSO2NGS_LCT_server.spec --distpath server_files
if errorlevel 1 (
    echo [ERROR] PyInstaller failed
    pause
    exit /b 1
)

npm run dist
if errorlevel 1 (
    echo [ERROR] electron-builder failed
    pause
    exit /b 1
)

echo.
echo ============================================
echo  BUILD SUCCESS! Output: release\
echo ============================================
explorer release
pause
