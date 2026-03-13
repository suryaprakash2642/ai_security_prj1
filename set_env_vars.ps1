# ============================================================
# set_env_vars.ps1
# Loads all vars from .env.local into the CURRENT terminal
# session only. Vars are gone when the terminal closes.
# Dot-source this file to keep them in scope:
#   . .\set_env_vars.ps1
# ============================================================

$BASE    = $PSScriptRoot
$envFile = "$BASE\.env.local"

if (-not (Test-Path $envFile)) {
    Write-Host '[ERROR] .env.local not found.' -ForegroundColor Red
    exit 1
}

$inMultiline = $false
$set = 0
$skip = 0

Get-Content $envFile | ForEach-Object {
    $line = $_

    # Detect start of multiline quoted value (RSA keys etc.) -- skip them entirely
    if ($line -match '^[A-Za-z_][A-Za-z0-9_]*=".*(-{5}BEGIN|-{5}END)') {
        $inMultiline = -not ($line -match '"$')
        $skip++
        return
    }
    if ($inMultiline) {
        if ($line -match '"$') { $inMultiline = $false }
        return
    }

    # Skip comments and blank lines
    if ($line -match '^\s*#' -or $line -match '^\s*$') { return }

    # Parse KEY=VALUE (value may be quoted with "")
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        $key = $Matches[1].Trim()
        $val = $Matches[2].Trim().Trim('"')

        [System.Environment]::SetEnvironmentVariable($key, $val, 'Process')
        Write-Host ('[SET  ] ' + $key) -ForegroundColor Green
        $set++
    }
}

Write-Host ''
Write-Host ('Done. ' + $set + ' variables set for this session (' + $skip + ' multiline skipped).') -ForegroundColor Cyan
Write-Host 'NOTE: vars exist only in this terminal window.' -ForegroundColor DarkYellow
