# ============================================================
#  WorldCup 2026 Analytics Hub - V2 启动脚本 (Windows PowerShell)
#  端口: 8001
#  适用: Windows 10/11 + PowerShell 5.1+ / PowerShell 7+
#  用法: powershell -ExecutionPolicy Bypass -File .\start.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "backend"
$Port = if ($env:V2_PORT) { $env:V2_PORT } else { 8001 }
$Host = if ($env:V2_HOST) { $env:V2_HOST } else { "0.0.0.0" }
$LogFile = Join-Path $BackendDir "logs\v2.log"
$LogsDir = Join-Path $BackendDir "logs"

# 创建 logs 目录
if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Path $LogsDir | Out-Null }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  WorldCup 2026 V2 启动 (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  端口: $Port"
Write-Host "  后端: $BackendDir"
Write-Host ""

# 检查 Python
$PythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $PythonCmd = $cmd
            Write-Host "[INFO] 检测到 $ver (命令: $cmd)" -ForegroundColor Green
            break
        }
    } catch { }
}
if (-not $PythonCmd) {
    Write-Host "[ERROR] python 不在 PATH 中" -ForegroundColor Red
    Write-Host "  请安装 Python 3.11+: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# 检查端口
$portInUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[ERROR] 端口 $Port 已被占用 (PID=$($portInUse.OwningProcess))" -ForegroundColor Red
    Write-Host "  停止: Stop-Process -Id $($portInUse.OwningProcess)" -ForegroundColor Yellow
    exit 1
}

# 检查依赖
try {
    python -c "import fastapi, uvicorn, apscheduler" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "missing" }
} catch {
    Write-Host "[WARN] 依赖未安装, 正在安装..." -ForegroundColor Yellow
    & $PythonCmd -m pip install -r (Join-Path $BackendDir "requirements-windows.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] 依赖安装失败" -ForegroundColor Red
        exit 1
    }
}

# 检查数据库
$dbPath = Join-Path $BackendDir "data\wc2026.db"
if (-not (Test-Path $dbPath)) {
    Write-Host "[WARN] 数据库不存在, 正在初始化..." -ForegroundColor Yellow
    Push-Location $BackendDir
    & $PythonCmd seed.py
    Pop-Location
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] 数据库初始化失败" -ForegroundColor Red
        exit 1
    }
}

# 启动
Write-Host "[INFO] 启动 V2 后端..." -ForegroundColor Green
Push-Location $BackendDir
$proc = Start-Process -FilePath $PythonCmd -ArgumentList @(
    "-m", "uvicorn", "app:app", "--host", $Host, "--port", $Port
) -RedirectStandardOutput $LogFile -RedirectStandardError (Join-Path $LogsDir "v2.err.log") -NoNewWindow -PassThru
Pop-Location
Write-Host "[INFO] V2 PID = $($proc.Id)"

# 健康检查
Start-Sleep -Seconds 3
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
    Write-Host ""
    Write-Host "[OK] V2 启动成功" -ForegroundColor Green
    Write-Host "    状态:    $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
    Write-Host ""
    Write-Host "    主页:    http://localhost:$Port/" -ForegroundColor Cyan
    Write-Host "    准确率:  http://localhost:$Port/#accuracy" -ForegroundColor Cyan
    Write-Host "    API:     http://localhost:$Port/docs" -ForegroundColor Cyan
    Write-Host "    日志:    Get-Content '$LogFile' -Wait" -ForegroundColor Gray
    Write-Host ""
    Write-Host "    停止:    powershell -File .\stop.ps1" -ForegroundColor Yellow
    Write-Host "    状态:    powershell -File .\status.ps1" -ForegroundColor Yellow
    Write-Host ""
} catch {
    Write-Host "[ERROR] V2 健康检查失败" -ForegroundColor Red
    if (Test-Path $LogFile) { Get-Content $LogFile -Tail 20 }
    exit 1
}
