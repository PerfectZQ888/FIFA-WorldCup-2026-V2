@echo off
REM ============================================================
REM  WorldCup 2026 Analytics Hub - V2 启动脚本 (Windows)
REM  端口: 8001
REM  适用: Windows 10/11 + Python 3.11+
REM ============================================================
setlocal EnableDelayedExpansion

REM 切到脚本所在目录
cd /d "%~dp0"

REM 配置
set PORT=8001
set HOST=0.0.0.0
set BACKEND_DIR=%cd%\backend
set PID_FILE=%BACKEND_DIR%\logs\v2.pid
set LOG_FILE=%BACKEND_DIR%\logs\v2.log

REM 创建 logs 目录
if not exist "%BACKEND_DIR%\logs" mkdir "%BACKEND_DIR%\logs"

echo.
echo ============================================================
echo  WorldCup 2026 V2 启动 (Windows)
echo ============================================================
echo  端口: %PORT%
echo  后端: %BACKEND_DIR%
echo.

REM 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] python 不在 PATH 中
    echo   请安装 Python 3.11+ 并加入 PATH: https://www.python.org/downloads/
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [INFO] 检测到 Python !PYVER!

REM 检查端口占用 (用 netstat, 跨 Windows 版本兼容)
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] 端口 %PORT% 已被占用
    netstat -ano | findstr ":%PORT% " | findstr "LISTENING"
    echo   停止占用进程: taskkill /PID <PID> /F
    if exist "%PID_FILE%" (
        echo   或者运行 stop.bat 停止旧 V2 实例
    )
    exit /b 1
)

REM 检查依赖
python -c "import fastapi, uvicorn, apscheduler" 2>nul
if errorlevel 1 (
    echo [WARN] 依赖未安装, 正在安装...
    python -m pip install -r "%BACKEND_DIR%\requirements-windows.txt"
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败
        exit /b 1
    )
)

REM 检查数据库
if not exist "%BACKEND_DIR%\data\wc2026.db" (
    echo [WARN] 数据库不存在, 正在初始化...
    cd /d "%BACKEND_DIR%" && python seed.py
    if errorlevel 1 (
        echo [ERROR] 数据库初始化失败
        exit /b 1
    )
    cd /d "%~dp0"
)

REM 启动 (用 pythonw / 隐藏窗口, 或 python -m uvicorn)
echo [INFO] 启动 V2 后端...
cd /d "%BACKEND_DIR%"
start /B python -m uvicorn app:app --host %HOST% --port %PORT% > "%LOG_FILE%" 2>&1
echo %errorlevel% > "%PID_FILE%"

REM 健康检查
timeout /t 3 /nobreak >nul
curl -sf -m 3 "http://127.0.0.1:%PORT%/api/health" >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [OK] V2 启动成功 ^(端口 %PORT%^)
    echo.
    echo   主页:    http://localhost:%PORT%/
    echo   准确率:  http://localhost:%PORT%/#accuracy
    echo   API:     http://localhost:%PORT%/docs
    echo   日志:    type %LOG_FILE%
    echo.
    echo   停止:    stop.bat
    echo   状态:    status.bat
    echo.
) else (
    echo [ERROR] V2 启动失败, 查看日志: type %LOG_FILE%
    type %LOG_FILE%" 2>nul | more
    exit /b 1
)

endlocal
