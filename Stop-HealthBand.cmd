@echo off
setlocal

cd /d "%~dp0"

title Stop HealthBand

echo.
echo Stopping HealthBand...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR:
    echo Virtual environment was not found.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" ^
    -m scripts.run_healthband_desktop ^
    --stop

echo.
echo HealthBand stop command completed.
echo.

timeout /t 2 >nul

endlocal