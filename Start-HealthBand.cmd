@echo off
setlocal

cd /d "%~dp0"

title HealthBand Launcher

echo.
echo ========================================
echo              HEALTHBAND
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR:
    echo Virtual environment was not found.
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

".venv\Scripts\python.exe" ^
    -m scripts.run_healthband_desktop ^
    --stop >nul 2>&1

echo Starting current HealthBand release...
echo.

".venv\Scripts\python.exe" ^
    -m scripts.run_healthband_desktop

if errorlevel 1 (
    echo.
    echo HealthBand failed to start.
    echo.
    pause
)

endlocal