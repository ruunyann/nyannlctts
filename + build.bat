@echo off
title PSO2NGS LCT - Build

echo ============================================
echo  PSO2NGS LCT - Build Script
echo ============================================
echo.

echo [1/4] Checking Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo [2/4] Installing Python packages...
pip install flask flask-socketio pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)
echo       OK

echo.
echo [3/4] Building Python server to EXE...
pyinstaller --onefile --noconsole --name PSO2NGS_LCT_server --distpath server_files server_files\PSO2NGS_LCT_server.py
if errorlevel 1 (
    echo [ERROR] PyInstaller failed
    pause
    exit /b 1
)
echo       OK - server_files\PSO2NGS_LCT_server.exe

echo.
echo [4/4] Building Electron app...
node --version
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    echo         https://nodejs.org/
    pause
    exit /b 1
)

npm install
if errorlevel 1 (
    echo [ERROR] npm install failed
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
