# ============================================================
# Apollo Hospitals Zero Trust NL-to-SQL — Start All Services
# ============================================================
# Usage:  .\start_all.ps1
# Stop:   .\stop_all.ps1
# ============================================================

$BASE    = $PSScriptRoot
$LOG_DIR = "$BASE\logs"
$PID_FILE = "$BASE\.service_pids.txt"

New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null
'' | Set-Content $PID_FILE

# -- Load .env.local into the current process environment ----
# Each service also loads its own .env via python-dotenv,
# but setting them here ensures they are INHERITED by child
# processes (especially L3 which has no .env file of its own).
# Note: python-dotenv does NOT override already-set env vars,
# so values set here take precedence over per-service .env files.
$envFile = "$BASE\.env.local"
if (Test-Path $envFile) {
    $inMultiline = $false
    Get-Content $envFile | ForEach-Object {
        $line = $_
        # Start of a multiline quoted value (e.g. RSA keys) - skip until closing quote
        if ($line -match '^[A-Z_]+=".*(-{5}BEGIN|-{5}END)') {
            $inMultiline = -not ($line -match '"$')
            return
        }
        if ($inMultiline) {
            if ($line -match '"$') { $inMultiline = $false }
            return
        }
        # Normal KEY=VALUE line (skip comments and blanks)
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $key = $Matches[1].Trim()
            $val = $Matches[2].Trim().Trim('"')
            [System.Environment]::SetEnvironmentVariable($key, $val, 'Process')
        }
    }
    Write-Host '[INFO ] Loaded .env.local' -ForegroundColor Cyan
}

# -- Override inter-service URLs and Redis for local dev -----
$env:REDIS_URL        = 'redis://:dj5Q0zOOQst62LGwNHvfnxZ3PIu7qtAE@redis-10791.crce219.us-east-1-4.ec2.cloud.redislabs.com:10791/0'
$env:L1_REDIS_URL     = 'redis://:dj5Q0zOOQst62LGwNHvfnxZ3PIu7qtAE@redis-10791.crce219.us-east-1-4.ec2.cloud.redislabs.com:10791/0'
$env:L2_REDIS_URL     = 'redis://:dj5Q0zOOQst62LGwNHvfnxZ3PIu7qtAE@redis-10791.crce219.us-east-1-4.ec2.cloud.redislabs.com:10791/0'
$env:L3_REDIS_URL     = 'redis://:dj5Q0zOOQst62LGwNHvfnxZ3PIu7qtAE@redis-10791.crce219.us-east-1-4.ec2.cloud.redislabs.com:10791/0'
$env:L3_L2_BASE_URL   = 'http://localhost:8002'
$env:L3_L4_BASE_URL   = 'http://localhost:8400'
$env:L8_AUDIT_URL     = 'http://localhost:8800'
$env:VAULT_ENABLED    = 'false'

# -- Helpers -------------------------------------------------
function Test-PortInUse($port) {
    $result = netstat -ano 2>$null | Select-String "TCP.*:$port\s.*LISTENING"
    return ($null -ne $result)
}

function Start-Service($name, $dir, $venv, $module, $port) {
    if (Test-PortInUse $port) {
        Write-Host ('[SKIP ] ' + $name + ' already running on port ' + $port) -ForegroundColor Yellow
        return
    }

    $python = "$script:BASE\.venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        Write-Host '[WARN ] Root .venv not found. Run from project root:' -ForegroundColor Yellow
        Write-Host '         python -m venv .venv' -ForegroundColor DarkYellow
        Write-Host '         .venv\Scripts\pip install -r all_reqs.txt' -ForegroundColor DarkYellow
        return
    }

    Write-Host ('[START] ' + $name + ' on port ' + $port + ' ...') -ForegroundColor Green

    $sparams = @{
        FilePath               = $python
        ArgumentList           = @('-m', 'uvicorn', $module, '--host', '0.0.0.0', '--port', "$port")
        WorkingDirectory       = $dir
        RedirectStandardOutput = "$LOG_DIR\$name.log"
        RedirectStandardError  = "$LOG_DIR\$name-err.log"
        PassThru               = $true
        WindowStyle            = 'Hidden'
    }
    $proc = Start-Process @sparams

    Add-Content $PID_FILE "$($proc.Id) $name"
    Write-Host ('        PID ' + $proc.Id + '  ->  ' + $LOG_DIR + '\' + $name + '.log')
    Start-Sleep -Milliseconds 400
}

# -- Banner --------------------------------------------------
Write-Host ''
Write-Host 'o======================================================o'
Write-Host '|    Apollo Hospitals Zero Trust NL-to-SQL Pipeline    |'
Write-Host 'o======================================================o'
Write-Host ''

# -- Start layer services ------------------------------------
Start-Service 'L1-identity'   "$BASE\l1-identity-context"      '.venv' 'app.main:app' 8001
Start-Service 'L2-knowledge'  "$BASE\l2-knowledge-graph-v3"    '.venv' 'app.main:create_app' 8002
Start-Service 'L3-retrieval'  "$BASE\l3-intelligent-retrieval" '.venv' 'app.main:app' 8300
Start-Service 'L4-policy'     "$BASE\l4-policy-resolution"     'venv'  'app.api.main:app' 8400
Start-Service 'L5-generation' "$BASE\l5-secure-generation"     '.venv' 'app.main:app' 8500
Start-Service 'L6-validation' "$BASE\l6-multi-gate-validation" '.venv' 'app.main:app' 8600
Start-Service 'L7-execution'  "$BASE\l7-secure-execution"      'venv'  'app.main:app' 8700
Start-Service 'L8-audit'      "$BASE\l8-audit-anomaly"         'venv'  'app.main:app' 8800

# -- React frontend on port 3001 ----------------------------
$reactDir = "$BASE\react-frontend"
if (-not (Test-Path $reactDir)) {
    Write-Host '[WARN ] react-frontend directory not found - skipping' -ForegroundColor Yellow
} elseif (Test-PortInUse 3001) {
    Write-Host '[SKIP ] React frontend already running on port 3001' -ForegroundColor Yellow
} else {
    $npmExe = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
    if ($npmExe) {
        Write-Host '[START] React frontend on port 3001 ...' -ForegroundColor Green
        $fparams = @{
            FilePath               = $npmExe
            ArgumentList           = @('run', 'dev')
            WorkingDirectory       = $reactDir
            RedirectStandardOutput = "$LOG_DIR\frontend.log"
            RedirectStandardError  = "$LOG_DIR\frontend-err.log"
            PassThru               = $true
            WindowStyle            = 'Hidden'
        }
        $fproc = Start-Process @fparams
        Add-Content $PID_FILE "$($fproc.Id) frontend"
        Write-Host ('        PID ' + $fproc.Id + '  ->  ' + $LOG_DIR + '\frontend.log')
    } else {
        Write-Host '[WARN ] npm not found in PATH - React frontend not started' -ForegroundColor Yellow
    }
}

# -- Wait for boot -------------------------------------------
Write-Host ''
Write-Host '[INFO ] Waiting 8s for services to boot...' -ForegroundColor Cyan
Start-Sleep -Seconds 8

# -- Health checks -------------------------------------------
Write-Host ''
Write-Host 'o======================================================o'
Write-Host '|                   Service Status                    |'
Write-Host 'o======================================================o'

function Check-Health($name, $url) {
    try {
        $resp = Invoke-WebRequest -Uri $url -TimeoutSec 4 -UseBasicParsing -ErrorAction Stop
        Write-Host ('  [OK] ' + $name + '  (' + $url + ')') -ForegroundColor Green
    } catch {
        Write-Host ('  [XX] ' + $name + '  (' + $url + ')') -ForegroundColor Red
    }
}

Check-Health 'L1 Identity'   'http://localhost:8001/health'
Check-Health 'L2 Knowledge'  'http://localhost:8002/health'
Check-Health 'L3 Retrieval'  'http://localhost:8300/api/v1/retrieval/health'
Check-Health 'L4 Policy'     'http://localhost:8400/health'
Check-Health 'L5 Generation' 'http://localhost:8500/health'
Check-Health 'L6 Validation' 'http://localhost:8600/health'
Check-Health 'L7 Execution'  'http://localhost:8700/health'
Check-Health 'L8 Audit'      'http://localhost:8800/health'
Check-Health 'React Frontend' 'http://localhost:3001'

# -- Summary -------------------------------------------------
Write-Host ''
Write-Host 'Frontend:    http://localhost:3001  (React + Vite)' -ForegroundColor Green
Write-Host 'Swagger UIs:' -ForegroundColor Green
Write-Host '  L1: http://localhost:8001/docs   L5: http://localhost:8500/docs'
Write-Host '  L2: http://localhost:8002/docs   L6: http://localhost:8600/docs'
Write-Host '  L3: http://localhost:8300/docs   L7: http://localhost:8700/docs'
Write-Host '  L4: http://localhost:8400/docs   L8: http://localhost:8800/docs'
Write-Host ''
Write-Host ('Logs : ' + $LOG_DIR)
Write-Host ('PIDs : ' + $PID_FILE)
Write-Host ''
Write-Host 'To stop all services: .\stop_all.ps1' -ForegroundColor Cyan
