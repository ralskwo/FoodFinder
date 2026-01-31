@echo off
chcp 65001 >nul
echo ============================================================
echo 🛑 FoodFinder 애플리케이션 종료
echo ============================================================
echo.

echo 🔍 실행 중인 서버 프로세스 확인 중...
echo.

REM Python 백엔드 프로세스 종료
echo 📦 백엔드 서버 종료 중...
taskkill /FI "WINDOWTITLE eq FoodFinder Backend*" /F 2>nul
if %errorlevel% equ 0 (
    echo ✅ 백엔드 서버 종료 완료
) else (
    echo ℹ️  실행 중인 백엔드 서버가 없습니다
)

echo.

REM Node.js 프론트엔드 프로세스 종료
echo 🌐 프론트엔드 서버 종료 중...
taskkill /FI "WINDOWTITLE eq FoodFinder Frontend*" /F 2>nul
if %errorlevel% equ 0 (
    echo ✅ 프론트엔드 서버 종료 완료
) else (
    echo ℹ️  실행 중인 프론트엔드 서버가 없습니다
)

echo.
echo ============================================================
echo ✅ 종료 완료!
echo ============================================================
echo.
pause
