# PowerShell Core script for macOS
# Usage: ./onedrive_size.ps1 "/path/to/target"

param(
    [string]$TargetPath = $args[0]
)

if (-not (Test-Path -LiteralPath $TargetPath)) {
    Write-Host "❌ Path not found: $TargetPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n📦 Calculating size of target directory:" -ForegroundColor Cyan
Write-Host "$TargetPath`n"

function Get-FolderSize {
    param([string]$FolderPath)

    $size = (Get-ChildItem -LiteralPath $FolderPath -Recurse -Force -ErrorAction SilentlyContinue |
             Where-Object { -not $_.PSIsContainer -and $_.Length -ge 0 } |
             Measure-Object -Property Length -Sum).Sum
    return $size
}

# Total size of target directory
$targetSize = Get-FolderSize -FolderPath $TargetPath
Write-Host "📁 Total size of '$TargetPath': $([math]::Round($targetSize / 1GB, 2)) GB`n"

# Sizes of immediate subdirectories
Write-Host "📂 Subfolder sizes:" -ForegroundColor Cyan

$results = @()

Get-ChildItem -LiteralPath $TargetPath -Directory -Force | ForEach-Object {
    $folder = $_.FullName
    $size = Get-FolderSize -FolderPath $folder
    $results += [PSCustomObject]@{
        Folder = $_.Name
        SizeGB = [math]::Round($size / 1GB, 2)
    }
}

$results | Sort-Object SizeGB -Descending | Format-Table -AutoSize
