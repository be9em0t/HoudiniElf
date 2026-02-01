<#
.SYNOPSIS
  Launch ComfyUI from the repository virtual environment and open the UI in the browser after verifying the server is up.

.DESCRIPTION
  - Starts ComfyUI in a new PowerShell window (interactive) or in background with venv activation.
  - Uses the ComfyUI folder as the working directory to make execution stable when relative imports or resources are used.
  - Polls the HTTP interface every $PollIntervalSeconds until it responds or the timeout ($TimeoutSeconds) expires.
  - When started with `-Background` the launcher will activate the venv in a hidden PowerShell, start the Python process detached and write its PID to `$PidFile`.
  - Use `stop_ComfyUI.ps1` to stop a background instance (reads the same PID file). Use `status_ComfyUI.ps1` to inspect status and HTTP responsiveness.

.PARAMETER VenvPath
  Path to the virtual environment. Defaults to the repository-local `.venv` (same directory as this script).

.PARAMETER TimeoutSeconds
  Maximum number of seconds to wait for the HTTP interface to become responsive (default: 60).

.PARAMETER PollIntervalSeconds
  How often to poll the URL in seconds (default: 1).

.PARAMETER HostName
  Host/IP to check (default: 127.0.0.1). Use `-HostName` to override.

.PARAMETER Port
  Port used by ComfyUI (default: 8188).

.PARAMETER ComfySubdir
  Subdirectory inside the repository that contains ComfyUI. Default: 'ComfyUI'.

.PARAMETER Background
  Switch. When specified, start ComfyUI detached (no interactive window). The launcher creates `$PidFile` containing the background process ID so it can be stopped later.

.PARAMETER PidFile
  Path to the PID file written when `-Background` is used. Default: `comfyui.pid` in the script directory. Used by `stop_ComfyUI.ps1` and `status_ComfyUI.ps1`.

.EXAMPLE
  .\launch_ComfyUI.ps1
  Start ComfyUI interactively (keeps a PowerShell window open with the venv activated).

  .\launch_ComfyUI.ps1 -Background
  Start ComfyUI in background; PID file is written to `comfyui.pid`.

  .\launch_ComfyUI.ps1 -Background -PidFile 'C:\temp\comfy.pid'
  Start background instance and write PID to a custom location.

  .\launch_ComfyUI.ps1 -TimeoutSeconds 120
  Increase wait time for the UI to become ready.

  .\stop_ComfyUI.ps1
  Stops the background ComfyUI using the default PID file.

  .\status_ComfyUI.ps1
  Shows whether a background ComfyUI is running and whether the HTTP interface is responding.

#>

param(
    [string]$VenvPath = (Join-Path $PSScriptRoot '.venv'),
    [int]$TimeoutSeconds = 60,
    [int]$PollIntervalSeconds = 1,
    [string]$HostName = '127.0.0.1',
    [int]$Port = 8188,
    [string]$ComfySubdir = 'ComfyUI',
    [switch]$Background,
    [string]$PidFile = (Join-Path $PSScriptRoot 'comfyui.pid')
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
    if ($Background) {
        # Background/detached start: write PID to $PidFile so the process can be stopped later
        if (Test-Path -Path $PidFile) {
            try {
                $existingPid = [int](Get-Content -Path $PidFile -ErrorAction Stop).Trim()
                if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
                    Write-Err "An instance appears to be running (PID $existingPid). Stop it first or remove $PidFile"
                    exit 3
                }
                else {
                    Write-Warn "Removing stale PID file: $PidFile"
                    Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
                }
            }
            catch {
                Write-Warn "Could not read existing PID file; removing it."
                Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
            }
        }

        Write-Info "Starting ComfyUI in background (venv activated) and writing PID to $PidFile"
        # Inner command: activate venv, start python as a detached process, then write its PID to the pid file
        $inner = "Set-Location -Path '$ComfyDir'; . '$ActivatePs1'; `$p = Start-Process -FilePath 'python' -ArgumentList `"`"$MainPy`" --enable-manager`" -WorkingDirectory '$ComfyDir' -PassThru -WindowStyle Hidden; `$p.Id | Out-File -FilePath '$PidFile' -Encoding ASCII"
        $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-Command', $inner)

        $launcher = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList -WorkingDirectory $ComfyDir -PassThru
        Write-Info "Launched hidden launcher process Id: $($launcher.Id). Waiting for PID file..."
        $pidDeadline = (Get-Date).AddSeconds(10)
        while ((Get-Date) -lt $pidDeadline -and -not (Test-Path -Path $PidFile)) { Start-Sleep -Milliseconds 200 }
        if (Test-Path -Path $PidFile) {
            $newPid = (Get-Content -Path $PidFile).Trim()
            Write-Info "ComfyUI started (PID $newPid)"
        }
        else {
            Write-Warn "PID file was not created. Background start may have failed."
        }
    }
    else {
        Write-Info "Starting ComfyUI in a new PowerShell window and activating venv: $ActivatePs1"
        # Build a PowerShell command that: cd to Comfy dir, source Activate.ps1, then run python main.py --enable-manager
        $psCommand = "Set-Location -Path '$ComfyDir'; . '$ActivatePs1'; python `"$MainPy`" --enable-manager"
        # Use -NoProfile to avoid loading user profiles (prevents errors from missing dot-sourced files)
        $argList = @('-NoProfile', '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $psCommand)

        # Start a new PowerShell window so the venv activation is visible and any subprocesses use the activated venv.
        $proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList -WorkingDirectory $ComfyDir -WindowStyle Normal -PassThru
        Write-Info "Launched PowerShell window (process Id: $($proc.Id))"
    }
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
