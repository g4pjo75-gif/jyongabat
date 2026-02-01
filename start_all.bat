@echo off
setlocal
echo ===================================================
echo  KR Market Project - Unified Starter
echo ===================================================
echo.

REM PYTHONPATH fix (from run_fixed.bat)
set PYTHONPATH=%PYTHONPATH%;C:\Users\wawoo\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages
set PYTHONIOENCODING=utf-8

echo [1/2] Starting Flask Backend (Port 5001)...
start "Flask Backend" cmd /c "python flask_app.py"

echo [2/2] Starting Next.js Frontend (Port 3000)...
if exist "frontend" (
    cd frontend
    start "Next.js Dashboard" cmd /c "npm run dev"
    cd ..
) else (
    echo [ERROR] 'frontend' directory not found!
)

echo.
echo ===================================================
echo  [SUCCESS] All services are starting up.
echo  - Backend: http://localhost:5001
echo  - Frontend: http://localhost:3000
echo.
echo  [TIP] To stop all services, run stop_services.bat
echo ===================================================
echo.
pause
endlocal
