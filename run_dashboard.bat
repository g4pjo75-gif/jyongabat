@echo off
setlocal
echo ===================================================
echo  KR Market Project - Dashboard Launcher (Next.js)
echo ===================================================
echo.

REM frontend 디렉토리로 이동
if exist "frontend" (
    cd frontend
) else (
    echo [ERROR] 'frontend' directory not found!
    pause
    exit /b
)

echo [INFO] Starting Next.js Dashboard...
echo [INFO] Once started, visit: http://localhost:3000
echo.

REM 개발 서버 실행
npm run dev

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Dashboard failed to start.
    echo Make sure Node.js is installed and 'npm install' was run in the frontend folder.
    pause
)

endlocal
