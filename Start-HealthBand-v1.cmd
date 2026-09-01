@echo off
setlocal

cd /d "%~dp0"

title HealthBand Demo Launcher

echo.
echo ========================================
echo       HEALTHBAND DEMO - VERSION 1
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR:
    echo Virtual environment was not found.
    echo.
    echo Expected:
    echo .venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import webview" >nul 2>&1

if errorlevel 1 (
    echo ERROR:
    echo pywebview is not installed.
    echo.
    echo Run:
    echo .venv\Scripts\python.exe -m pip install pywebview
    echo.
    pause
    exit /b 1
)

echo Stopping previously recorded HealthBand processes...

".venv\Scripts\python.exe" ^
    -m scripts.run_healthband_desktop ^
    --stop >nul 2>&1

echo.
echo Starting clean HealthBand 1.0.0 demo...
echo.

".venv\Scripts\python.exe" ^
    -m scripts.run_healthband_desktop ^
    --reset-v1

if errorlevel 1 (
    echo.
    echo HealthBand failed to start.
    echo.
    pause
)

endlocal