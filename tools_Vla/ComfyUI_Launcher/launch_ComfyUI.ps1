<#
.SYNOPSIS
  Start ComfyUI using the repository virtual environment and open the UI in the browser when ready.

.DESCRIPTION
  Starts ComfyUI in a new PowerShell window with the virtual environment activated and waits until the web UI responds before opening the browser.

.PARAMETER VenvPath
  Path to the virtual environment (default: .\.venv in the script directory).

.PARAMETER TimeoutSeconds
  Seconds to wait for the UI to respond (default: 60).

.PARAMETER PollIntervalSeconds
  Poll interval in seconds (default: 1).

.PARAMETER HostName
  Host/IP to check (default: 127.0.0.1).

.PARAMETER Port
  Port used by ComfyUI (default: 8188).

.PARAMETER ComfySubdir
  Subdirectory containing ComfyUI (default: 'ComfyUI').

.EXAMPLE
  .\launch_ComfyUI.ps1
#>

param(
    [string]$VenvPath = (Join-Path $PSScriptRoot '.venv'),
    [int]$TimeoutSeconds = 60,
    [int]$PollIntervalSeconds = 1,
    [string]$HostName = '127.0.0.1',
    [int]$Port = 8188,
    [string]$ComfySubdir = 'ComfyUI'
)

Set-StrictMode -Version Latest

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host "[INFO ] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN ] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Resolve paths
$VenvPath = [System.IO.Path]::GetFullPath($VenvPath)
$ComfyDir = Join-Path $PSScriptRoot $ComfySubdir
$PythonExe = Join-Path $VenvPath 'Scripts\python.exe'
$MainPy = Join-Path $ComfyDir 'main.py'
$Url = "http://$HostName`:$Port"

Write-Info "Using script root: $PSScriptRoot"
Write-Info "Venv path: $VenvPath"
Write-Info "ComfyUI dir: $ComfyDir"
Write-Info "URL to check: $Url"

# Validate files and folders
if (-not (Test-Path -Path $VenvPath -PathType Container)) {
    Write-Err "Virtual environment not found at: $VenvPath"
    Write-Err "Please create the venv or pass -VenvPath pointing to a valid virtual environment.";
    exit 1
}

if (-not (Test-Path -Path $PythonExe -PathType Leaf)) {
    Write-Err "python.exe not found in virtual environment at: $PythonExe"
    Write-Err "Make sure the venv is created correctly and contains Scripts\python.exe"
    exit 1
}

if (-not (Test-Path -Path $ComfyDir -PathType Container)) {
    Write-Err "ComfyUI directory not found at: $ComfyDir"
    exit 1
}

if (-not (Test-Path -Path $MainPy -PathType Leaf)) {
    Write-Err "main.py not found at: $MainPy"
    exit 1
}

# Start ComfyUI in a new PowerShell window with the venv explicitly activated and ComfyUI dir as working directory.
$ActivatePs1 = Join-Path $VenvPath 'Scripts\Activate.ps1'
if (-not (Test-Path -Path $ActivatePs1 -PathType Leaf)) {
    Write-Err "Activate.ps1 not found at: $ActivatePs1"
    Write-Err "PowerShell activation not available; ensure the venv was created with PowerShell activation scripts."
    exit 1
}
try {
    Write-Info "Starting ComfyUI in a new PowerShell window and activating venv: $ActivatePs1"
    # Build a PowerShell command that: cd to Comfy dir, source Activate.ps1, then run python main.py --enable-manager
    $psCommand = "Set-Location -Path '$ComfyDir'; . '$ActivatePs1'; python `"$MainPy`" --enable-manager"
    # Use -NoProfile to avoid loading user profiles (prevents errors from missing dot-sourced files)
    $argList = @('-NoProfile', '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $psCommand)

    # Start a new PowerShell window so the venv activation is visible and any subprocesses use the activated venv.
    $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList -WorkingDirectory $ComfyDir -WindowStyle Normal -PassThru
    Write-Info "Launched PowerShell window (process Id: $($proc.Id))"
}
catch {
    Write-Err "Failed to launch ComfyUI: $_"
    exit 1
}

# Poll the HTTP interface until it responds or timeout
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$ok = $false
Write-Info "Waiting up to $TimeoutSeconds seconds for $Url to respond (poll interval: $PollIntervalSeconds s)"
while ((Get-Date) -lt $deadline) {
    try {
        # Invoke-WebRequest works in Windows PowerShell and PowerShell Core; we use a short timeout
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
            Write-Info "Server responded with HTTP $($response.StatusCode). Opening browser..."
            Start-Process $Url
            $ok = $true
            break
        }
        else {
            Write-Warn "Received HTTP $($response.StatusCode). Retrying..."
        }
    }
    catch {
        # Not ready yet; suppress details and sleep
        Start-Sleep -Seconds $PollIntervalSeconds
    }
}

if (-not $ok) {
    Write-Warn "Server did not respond within $TimeoutSeconds seconds. Not opening browser."
    Write-Warn "You can still open $Url manually or increase -TimeoutSeconds if ComfyUI needs more startup time."
    exit 2
}

exit 0
