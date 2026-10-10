@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0BULL-v0.29.0.1.ps1" -Surface agent
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%
