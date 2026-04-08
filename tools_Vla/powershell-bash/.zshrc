trap 'exit' SIGHUP

# Interactive shell settings
HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=100000

setopt HIST_IGNORE_DUPS
setopt HIST_FIND_NO_DUPS
setopt INC_APPEND_HISTORY
setopt SHARE_HISTORY

# Prefix-based history search (up/down after typing)
bindkey "^[[A" history-search-backward
bindkey "^[[B" history-search-forward

export ARTIFACTORY_USERNAME=vla.dunev@tomtom.com
export GIT_EDITOR="code --wait"
export PYTORCH_ENABLE_MPS_FALLBACK=1

alias term='open -a Terminal'
alias zfresh='exec zsh'
alias zsrc='source ~/.zshrc && echo "✅ .zshrc reloaded"'

# Git helpers
gs() {
  echo "Git Status:"
  git status
  echo ""
  echo "Repo: $(basename "$(git rev-parse --show-toplevel)")"
  echo "Remote: $(git remote get-url origin)"
  echo "Author: $(git config user.name) <$(git config user.email)>"
}

gco() {
  git checkout "$@"
}

gcout() {
  git checkout "$@"
}

gcm() {
  git commit -m "$@"
}

gcomm() {
  git commit -m "$@"
}

gex() {
  gh copilot explain "$@"
}

alias ga='git add .'
alias gadd='git add'
alias glog='git log --oneline'
alias glfs='git lfs ls-files'
alias gslfs='git lfs ls-files'
alias gpush='git push'
alias gurl='git config --get remote.origin.url'
alias gball='git branch --all'
alias gfet='git fetch --prune'
alias gf='git fetch --prune && git status -sb'
alias gsize='(git ls-files --others --exclude-standard && git diff --name-only) | sort -u | while IFS= read -r file; do if [ -f "$file" ] && [ "$(du -m "$file" | cut -f1)" -gt 42 ]; then echo "$file : $(du -h "$file" | cut -f1)"; fi; done'

alias py='python'
alias py3='python3'
alias pylist='pyenv versions'
alias pydeact='pyenv deactivate'
alias pyver='pyenv version'

pyact() {
  pyenv activate "$@"
}

# pyenv interactive init only; PATH setup lives in ~/.zprofile
export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init - --no-rehash)"
  eval "$(pyenv virtualenv-init -)"
fi

# Run Databricks keepalive in the current terminal
mcr_alive() {
  cd /Users/dunevv/WorkLocal/_AI_/HoudiniElf/tools_QGIS/dbQGIS || return

  if [ -f .env ]; then
    set -o allexport
    # shellcheck disable=SC1091
    source .env
    set +o allexport
  fi

  source /Users/dunevv/WorkLocal/_AI_/HoudiniElf/.venv/bin/activate
  dotenv run -- python databricks_keepalive2.py -c /dev/null -i 500
}

iterm() {
  open -a iTerm "$@"
}

alias caffeine='caffeinate -d'
alias wake='wakeonlan 60:CF:84:BC:9F:1B'
alias allow='sudo xattr -rd com.apple.quarantine'

# Keep this only when the target exists.
if [ -d /Users/dunevv/WorkLocal/_GIT_/AI/Ollama/models ]; then
  export OLLAMA_MODELS="/Users/dunevv/WorkLocal/_GIT_/AI/Ollama/models"
fi

set_prompt() {
  local blue=$'\e[38;2;76;167;248m'
  local reset=$'\e[0m'
  PROMPT="%{$blue%}%~ > %{$reset%}"
}
set_prompt

export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# Optional completions / interactive plugins
[[ -s "$HOME/.bun/_bun" ]] && source "$HOME/.bun/_bun"
# ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=244'
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=#7E939E"
[[ -r /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
[[ -r /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
