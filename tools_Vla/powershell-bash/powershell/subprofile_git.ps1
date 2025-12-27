
# == Git ===
#
# To enable autofetch:
# git config --global fetch.auto 1
# git config --global fetch.prune true

function Get-GitRemoteStatus {
    # Check if inside a git repo
    git rev-parse --is-inside-work-tree 2>$null
    if ($LASTEXITCODE -ne 0) { return "" }

    # Get branch ahead/behind info
    $status = git status --porcelain=v2 --branch 2>$null |
              Select-String "^# branch.ab"

    if (-not $status) { return "" }

    # Parse ahead/behind
    $parts = $status.ToString().Split(" ")
    $ahead  = ($parts[2] -replace "\+","") -as [int]
    $behind = ($parts[3] -replace "-","") -as [int]

    $out = ""
    if ($ahead  -gt 0) { $out += "⇡" }
    if ($behind -gt 0) { $out += "⇣" }

    return $out
}

$origPrompt = $function:prompt

function prompt {
    $gitStatus = Get-GitRemoteStatus
    "$gitStatus $(& $origPrompt)"
}

# == end Git ===
