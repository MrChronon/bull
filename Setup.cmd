@echo off
if exist "%~dp0Setup.exe" (
    start "" "%~dp0Setup.exe"
    exit /b 0
)
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup.ps1" -InstallDependencies
exit /b %errorlevel%
