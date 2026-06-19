$Port = if ($env:V2_PORT) { $env:V2_PORT } else { 8001 }
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  WorldCup 2026 V2 状态 (Windows)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  端口: $Port"
Write-Host ""
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "  [状态]  运行中 (PID=$($conn.OwningProcess))" -ForegroundColor Green
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
        Write-Host "  [健康]  $($h | ConvertTo-Json -Compress)" -ForegroundColor Green
    } catch {
        Write-Host "  [健康]  检查失败" -ForegroundColor Red
    }
} else {
    Write-Host "  [状态]  未运行" -ForegroundColor Gray
}
Write-Host ""
Write-Host "  主页:    http://localhost:$Port/" -ForegroundColor Cyan
Write-Host "  API:     http://localhost:$Port/docs" -ForegroundColor Cyan
