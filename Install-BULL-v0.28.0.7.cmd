@echo off
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-BULL-v0.28.0.7.ps1" -InstallDependencies
if errorlevel 1 (
  echo Установка BULL не завершена.
  pause
  exit /b 1
)
echo.
echo BULL настроен.
pause
