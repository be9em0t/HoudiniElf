<#
.SYNOPSIS
  Report status of a ComfyUI instance started with `launch_ComfyUI.ps1 -Background`.

.DESCRIPTION
  - Checks the PID file (default: `comfyui.pid`) and reports whether the process is running.
  - Optionally checks whether the web UI (`http://127.0.0.1:8188`) is responding and shows HTTP status.

.PARAMETER PidFile
  Path to the pid file created by the background launcher. Defaults to `comfyui.pid` in the script folder.

.PARAMETER Url
  URL to test for the ComfyUI web interface. Default: `http://127.0.0.1:8188`.

.EXAMPLE
  .\status_ComfyUI.ps1
  .\status_ComfyUI.ps1 -PidFile 'C:\temp\comfy.pid' -Url 'http://127.0.0.1:8188'
#>

param(
    [string]$PidFile = (Join-Path $PSScriptRoot 'comfyui.pid'),
    [string]$Url = 'http://127.0.0.1:8188'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host "[INFO ] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN ] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }

$running = $false

Write-Info "Checking PID file: $PidFile"
if (-not (Test-Path -Path $PidFile)) {
    Write-Warn "PID file not found. No background PID available."
}
else {
    try {
        $pidText = (Get-Content -Path $PidFile -ErrorAction Stop).Trim()
        $pidVal = [int]$pidText
        $proc = Get-Process -Id $pidVal -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Info "Found process: Id=$($proc.Id) Name=$($proc.ProcessName)"
            try { Write-Host "Start time: $($proc.StartTime)" -ForegroundColor Gray } catch {}
            $running = $true
        }
        else {
            Write-Warn "No process with PID $pidVal is running. PID file may be stale."
        }
    }
    catch {
        Write-Err "Could not read PID file or parse PID: $_"
    }
}

# Check the web interface
Write-Info "Checking web interface at: $Url"
try {
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
        Write-Info "HTTP $($resp.StatusCode) — interface responding"
        $webOk = $true
    }
    else {
        Write-Warn "HTTP $($resp.StatusCode) — not a successful status"
        $webOk = $false
    }
}
catch {
    Write-Warn "Interface not responding (request failed or timed out)."
    $webOk = $false
}

# Summary
Write-Host ""; Write-Host "=== Summary ===" -ForegroundColor Green
if ($running) { Write-Host "Background process: Running" -ForegroundColor Green } else { Write-Host "Background process: Not running" -ForegroundColor Yellow }
if ($webOk)   { Write-Host "Web interface : Responding" -ForegroundColor Green } else { Write-Host "Web interface : Not responding" -ForegroundColor Yellow }

if ($running -or $webOk) { exit 0 } else { exit 1 }