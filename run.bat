@echo off
chcp 65001 >nul
echo ============================================================
echo 🍽️  FoodFinder 애플리케이션 시작
echo ============================================================
echo.

REM 현재 디렉토리 저장
set ROOT_DIR=%~dp0

REM 백엔드 서버 시작 (새 창에서)
echo 📦 백엔드 서버 시작 중...
start "FoodFinder Backend" cmd /k "cd /d %ROOT_DIR%backend && python wsgi.py"

REM 잠시 대기 (백엔드가 먼저 시작되도록)
timeout /t 3 /nobreak >nul

REM 프론트엔드 서버 시작 (새 창에서)
echo 🌐 프론트엔드 서버 시작 중...
start "FoodFinder Frontend" cmd /k "cd /d %ROOT_DIR%frontend && npm start"

echo.
echo ============================================================
echo ✅ 서버 시작 완료!
echo ============================================================
echo.
echo 📍 백엔드: http://localhost:5000
echo 🌐 프론트엔드: http://localhost:3000
echo.
echo 💡 브라우저가 자동으로 열리지 않으면
echo    http://localhost:3000 을 직접 열어주세요.
echo.
echo ⚠️  서버를 종료하려면 각 창에서 Ctrl+C를 누르거나
echo    stop.bat을 실행하세요.
echo ============================================================
echo.
pause
