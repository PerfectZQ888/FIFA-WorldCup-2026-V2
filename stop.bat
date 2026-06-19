@echo off
REM WorldCup 2026 V2 停止 (Windows)
setlocal
set PORT=8001
set BACKEND_DIR=%~dp0backend
set PID_FILE=%BACKEND_DIR%\logs\v2.pid

echo 停止 V2 (端口 %PORT%) ...
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 端口 %PORT% 空闲, V2 未运行
    goto :end
)

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo [INFO] 停止 PID %%P ...
    taskkill /PID %%P /F >nul 2>&1
)
if exist "%PID_FILE%" del /f /q "%PID_FILE%" >nul 2>&1
echo [OK] V2 已停止
:end
endlocal
