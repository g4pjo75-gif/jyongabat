@echo off
setlocal
echo ===================================================
echo  KR Market Project - Service Stopper
echo ===================================================
echo.

echo [INFO] Searching for running services...

REM 5001번 포트 (Flask 백엔드) 종료
echo 1. Checking Flask Backend (Port 5001)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001') do (
    echo [FOUND] Killing process PID: %%a
    taskkill /F /PID %%a 2>nul
)

REM 3000번 포트 (Next.js 프론트엔드) 종료
echo 2. Checking Next.js Frontend (Port 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do (
    echo [FOUND] Killing process PID: %%a
    taskkill /F /PID %%a 2>nul
)

echo.
echo [SUCCESS] Service cleanup completed.
echo You can now close this window or restart the services.
echo.
pause
endlocal
