# kill_pythons.ps1

# Script to find and kill all running Python instances for cleanup.

$pythonProcesses = Get-Process | Where-Object { $_.ProcessName -like 'python*' } 

if ($pythonProcesses) {
    foreach ($proc in $pythonProcesses) {
        Write-Host "Killing process $($proc.Id) - $($proc.ProcessName)"
        Stop-Process -Id $proc.Id -Force
    }
} else {
    Write-Host "No Python processes found."
}