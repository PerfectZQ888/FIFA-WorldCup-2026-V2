$ErrorActionPreference = "Stop"
$Port = if ($env:V2_PORT) { $env:V2_PORT } else { 8001 }
Write-Host "停止 V2 (端口 $Port) ..." -ForegroundColor Yellow
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force
    Write-Host "[OK] V2 已停止 (PID=$($conn.OwningProcess))" -ForegroundColor Green
} else {
    Write-Host "[INFO] 端口 $Port 空闲, V2 未运行" -ForegroundColor Gray
}
