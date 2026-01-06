# Unblock downloaded script if pwsh refuses to load it

Write-Host "Profile: $PROFILE"
. "$HOME\Documents\PowerShell\subprofile_python.ps1"
. "$HOME\Documents\PowerShell\subprofile_git.ps1"
. "$HOME\Documents\PowerShell\subprofile_aliases.ps1"

function pwsrc {
    . $PROFILE
    . "$HOME\Documents\PowerShell\subprofile_python.ps1"
    . "$HOME\Documents\PowerShell\subprofile_git.ps1"
    . "$HOME\Documents\PowerShell\subprofile_aliases.ps1"
    Write-Host "✅ Profiles reloaded"
}

