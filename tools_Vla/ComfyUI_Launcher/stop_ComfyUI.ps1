<#
.SYNOPSIS
  Stops a background ComfyUI process started with `launch_ComfyUI.ps1 -Background` by reading the PID file.

.DESCRIPTION
  - Reads the PID from the default `comfyui.pid` file in the script folder (can be overridden).
  - Attempts to stop the process and removes the PID file on success or if the PID is stale.

.PARAMETER PidFile
  Path to the pid file created by the launcher. Defaults to `comfyui.pid` in the script directory.
#>

param(
    [string]$PidFile = (Join-Path $PSScriptRoot 'comfyui.pid')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host "[INFO ] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN ] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }

if (-not (Test-Path -Path $PidFile)) {
    Write-Err "PID file not found at: $PidFile"
    Write-Err "Is ComfyUI running in background? The launcher creates this file when started with -Background."
    exit 1
}

try {
    $pidText = (Get-Content -Path $PidFile -ErrorAction Stop).Trim()
    $pid = [int]$pidText
}
catch {
    Write-Err "Failed to read PID file: $_"
    exit 1
}

$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Warn "No process with PID $pid found. Removing stale PID file."
    Remove-Item -Path $PidFile -ErrorAction SilentlyContinue
    exit 0
}

try {
    Write-Info "Stopping process with PID $pid"
    Stop-Process -Id $pid -Force -ErrorAction Stop
    Start-Sleep -Seconds 1
    if (-not (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
        Write-Info "Process $pid stopped successfully. Removing PID file."
        Remove-Item -Path $PidFile -ErrorAction SilentlyContinue
        exit 0
    }
    else {
        Write-Warn "Process $pid still running after stop attempt."
        exit 2
    }
}
catch {
    Write-Err "Failed to stop process $pid: $_"
    exit 1
}