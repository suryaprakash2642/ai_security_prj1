# ============================================================
# Apollo Hospitals Zero Trust NL-to-SQL -- Stop All Services
# ============================================================
# Usage: .\stop_all.ps1
# ============================================================

$BASE     = $PSScriptRoot
$PID_FILE = "$BASE\.service_pids.txt"

if (-not (Test-Path $PID_FILE)) {
    Write-Host 'No PID file found -- killing by port' -ForegroundColor Yellow
    foreach ($port in @(8001, 8002, 8300, 8400, 8500, 8600, 8700, 8800, 3001)) {
        $lines = netstat -ano 2>$null | Select-String "TCP.*:$port\s.*LISTENING"
        foreach ($ln in $lines) {
            $procId = ($ln.ToString().Trim() -split '\s+')[-1]
            if ($procId -match '^\d+$' -and $procId -ne '0') {
                Stop-Process -Id ([int]$procId) -Force -ErrorAction SilentlyContinue
                Write-Host ('  Killed port ' + $port + ' (PID ' + $procId + ')') -ForegroundColor Green
            }
        }
    }
    exit 0
}

Get-Content $PID_FILE | ForEach-Object {
    if ($_ -match '^(\d+)\s+(.+)$') {
        $procId = [int]$Matches[1]
        $name   = $Matches[2]
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host ('  Stopped ' + $name + ' (PID ' + $procId + ')') -ForegroundColor Green
        } catch {
            Write-Host ('  ' + $name + ' (PID ' + $procId + ') not running') -ForegroundColor DarkGray
        }
    }
}

Remove-Item $PID_FILE -Force -ErrorAction SilentlyContinue
Write-Host ''
Write-Host 'All services stopped.' -ForegroundColor Cyan
