@echo off
if exist "%~dp0BULL.exe" (
    start "" "%~dp0BULL.exe"
    exit /b 0
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0BULL-v0.29.0.1.ps1"
