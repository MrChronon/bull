@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
where python >nul 2>nul
if errorlevel 1 (
    py -3 "Apps\agent_benchmark_v0_26_0_0.py"
) else (
    python "Apps\agent_benchmark_v0_26_0_0.py"
)
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%
