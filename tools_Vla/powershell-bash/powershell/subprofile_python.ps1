# Invoke-Expression (&starship init powershell)

Write-Host "PowerShell version: $($PSVersionTable.PSVersion)" -ForegroundColor Cyan


$global:LastVenvPath = ""

function Set-Location {
    param([string]$path)

    Microsoft.PowerShell.Management\Set-Location -Path $path

    $currentPath = (Get-Location).Path
    $venvPath = Join-Path $currentPath ".venv\Scripts\Activate.ps1"

    if ((Test-Path $venvPath) -and ($currentPath -ne $global:LastVenvPath)) {
        Write-Host "Activating .venv in $currentPath" -ForegroundColor Green
        . $venvPath
        $global:LastVenvPath = $currentPath
    } elseif (!(Test-Path $venvPath) -and $env:VIRTUAL_ENV) {
        Write-Host "Deactivating .venv from $global:LastVenvPath" -ForegroundColor Yellow      
        if (Get-Command deactivate -ErrorAction SilentlyContinue) {
            deactivate
        }
        $global:LastVenvPath = ""
    }
}
