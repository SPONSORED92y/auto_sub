@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
    echo.
    echo Installation failed. See docs\INSTALL_WINDOWS.md.
    pause
    exit /b 1
)
echo.
echo Double-click start.bat to launch.
pause
