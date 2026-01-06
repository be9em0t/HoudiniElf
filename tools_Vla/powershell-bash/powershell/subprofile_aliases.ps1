Write-Host "🔍 aliases reloaded"

# Git aliases and functions
function gs {
    Write-Host "🔍 Git Status:"
    git status
    Write-Host ""
    Write-Host "📦 Repo: \$((Split-Path (git rev-parse --show-toplevel) -Leaf))"
    Write-Host "🌐 Remote: \$(git remote get-url origin)"
    Write-Host "🧑 Author: \$(git config user.name) <\$(git config user.email)>"
}

Set-Alias ga "git add ."
Set-Alias gadd git
Set-Alias gslfs "git lfs ls-files"

function gsize {
    (git ls-files --others --exclude-standard) + (git diff --name-only) | Sort-Object -Unique | ForEach-Object {
        $file = $_
        if (Test-Path $file -PathType Leaf) {
            $sizeMB = [math]::Round((Get-Item $file).Length / 1MB)
            if ($sizeMB -gt 42) {
                $sizeHuman = if ($sizeMB -gt 1024) { [math]::Round($sizeMB / 1024, 1) + "G" } else { $sizeMB + "M" }
                "$file : $sizeHuman"
            }
        }
    }
}

Set-Alias gf "git fetch"
Set-Alias gpush "git push"
Set-Alias glfs "git lfs ls-files"
Set-Alias gurl "git config --get remote.origin.url"
Set-Alias gball "git branch --all"

Set-Alias vactivate ".\.venv\Scripts\activate"

function gex {
    param([string]$query)
    gh copilot explain $query
}

function gco {
    param([string]$branch)
    git checkout $branch
}

Set-Alias gcout gco

function gcm {
    param([string]$message)
    git commit -m $message
}

Set-Alias gcomm gcm

# but, of course, functions do not count as aliases
function aliases {
    $defaults = powershell -NoProfile -Command "Get-Alias | Select-Object -ExpandProperty Name"
    Get-Alias | Where-Object { $_.Name -notin $defaults } | Sort-Object Name | Format-Table Name, Definition -AutoSize
}
