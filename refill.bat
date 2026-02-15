@echo off
chcp 65001 >nul

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "BACKEND_PY=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "REFILL_SCRIPT=%BACKEND_DIR%\scripts\refill_cache.py"

if not exist "%REFILL_SCRIPT%" (
    echo [ERROR] Refill script not found: %REFILL_SCRIPT%
    goto :end
)

if not exist "%BACKEND_PY%" (
    echo [WARN] backend\.venv\Scripts\python.exe not found. Fallback to system python.
    set "BACKEND_PY=python"
)

echo Running cache refill...
"%BACKEND_PY%" "%REFILL_SCRIPT%" %*
echo.
echo Refill finished.

:end
pause
