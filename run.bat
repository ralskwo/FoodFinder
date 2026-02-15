@echo off
chcp 65001 >nul

echo ============================================================
echo FoodFinder servers startup
echo ============================================================

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "BACKEND_PY=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "BACKEND_REQ=%BACKEND_DIR%\requirements.txt"

if not exist "%BACKEND_DIR%\wsgi.py" (
    echo [ERROR] Backend directory is invalid: %BACKEND_DIR%
    goto :end
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo [ERROR] Frontend directory is invalid: %FRONTEND_DIR%
    goto :end
)

if not exist "%BACKEND_PY%" (
    echo [WARN] backend\.venv\Scripts\python.exe not found. Fallback to system python.
    set "BACKEND_PY=python"
)

if exist "%BACKEND_REQ%" (
    "%BACKEND_PY%" -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('bs4') else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [0/2] Installing backend dependencies...
        "%BACKEND_PY%" -m pip install -r "%BACKEND_REQ%"
        if errorlevel 1 (
            echo [WARN] Failed to install backend dependencies. Menu crawling may be limited.
        )
    )
)

echo [1/2] Starting backend...
start "FoodFinder Backend" /D "%BACKEND_DIR%" cmd /k ""%BACKEND_PY%" wsgi.py"

timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend...
start "FoodFinder Frontend" /D "%FRONTEND_DIR%" cmd /k "npm.cmd start"

echo.
echo Backend  : http://localhost:5000
echo Frontend : http://localhost:3000
echo.
echo Use stop.bat to stop both windows.
echo ============================================================

:end
pause
