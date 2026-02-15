@echo off
chcp 65001 >nul

echo ============================================================
echo FoodFinder servers shutdown
echo ============================================================
echo.

echo [1/2] Stop backend on port 5000...
for /f "tokens=5" %%I in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /PID %%I /F >nul 2>&1
)

echo [2/2] Stop frontend on port 3000...
for /f "tokens=5" %%I in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /PID %%I /F >nul 2>&1
)

REM Fallback by window title
taskkill /FI "WINDOWTITLE eq FoodFinder Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq FoodFinder Frontend*" /F >nul 2>&1

echo.
echo Done.
echo ============================================================
echo.
pause
