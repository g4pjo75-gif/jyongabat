@echo off
setlocal
REM 사용자 라이브러리 경로 추가 (설치된 패키지 인식 문제 해결)
set PYTHONPATH=%PYTHONPATH%;C:\Users\wawoo\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages

echo ===================================================
echo  KR Market Project - Fixed Launcher
echo ===================================================
echo.
echo [INFO] Setting PYTHONPATH for dependency resolution...
set PYTHONIOENCODING=utf-8
echo [TIP] 서비스를 완전히 종료하려면 stop_services.bat를 실행하세요.
echo.

python run.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application exited with error code %ERRORLEVEL%
    pause
)
endlocal
