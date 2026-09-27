@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-BULL-v0.24.0.0-Shortcut.ps1" -Quiet >nul 2>&1
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0BULL-v0.24.0.0.ps1"
