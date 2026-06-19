@echo off
setlocal
set PORT=8001
echo ============================================================
echo  WorldCup 2026 V2 状态 (Windows)
echo ============================================================
echo  端口: %PORT%
echo.

netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo  [状态]  运行中
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
        echo  [PID]   %%P
    )
    curl -s -m 3 http://127.0.0.1:%PORT%/api/health
    echo.
) else (
    echo  [状态]  未运行
)
echo.
echo  主页:    http://localhost:%PORT%/
echo  API:     http://localhost:%PORT%/docs
endlocal
