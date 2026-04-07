trap 'exit' SIGHUP

# Save and share history across sessions
HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=100000

setopt HIST_IGNORE_DUPS       # Don't store duplicate commands
setopt HIST_FIND_NO_DUPS      # Don't show duplicates when searching
setopt INC_APPEND_HISTORY     # Save history incrementally
setopt SHARE_HISTORY          # Share history across terminals

# Prefix-based history search (↑ / ↓ after typing)
bindkey "^[[A" history-search-backward   # ↑
bindkey "^[[B" history-search-forward    # ↓

# poetry
# PATH and tool roots consolidated to ~/.zprofile for faster interactive shells
export ARTIFACTORY_USERNAME=vla.dunev@tomtom.com

alias term='open -a Terminal'
alias zfresh='exec zsh'
alias zsrc='source ~/.zshrc && echo "✅ .zshrc reloaded"'

#git

gs() {
  echo "🔍 Git Status:"
  git status
  # --short
  echo ""
  echo "📦 Repo: $(basename "$(git rev-parse --show-toplevel)")"
  echo "🌐 Remote: $(git remote get-url origin)"
  echo "🧑 Author: $(git config user.name) <$(git config user.email)>"
}
alias ga='git add .'
alias gadd='git add'
# alias gs='git status'
alias gslfs='git lfs ls-files'
alias gsize='(git ls-files --others --exclude-standard && git diff --name-only) | sort -u | while IFS= read -r file; do
    if [ -f "$file" ] && [ $(du -m "$file" | cut -f1) -gt 42 ]; then
        echo "$file : $(du -h "$file" | cut -f1)"
    fi
done'
alias gpush='git push'
alias glog='git log --oneline'
alias glfs='git lfs ls-files'
alias gurl='git config --get remote.origin.url'
alias gball='git branch --all'
alias gex='function _gcm() { gh copilot explain "$@"; }; _gcm'

alias gco='function _gco() { git checkout "$@"; }; _gco'
alias gcout='function _gco() { git checkout "$@"; }; _gco'
alias gcm='function _gcm() { git commit -m "$@"; }; _gcm'
alias gcomm='function _gcm() { git commit -m "$@"; }; _gcm'

# alias py='echo "Select python version: \n- py3 for latest homebrew \n- py311 for python 3.11 \n- pylist for installed environments"'
# alias py3='/opt/homebrew/bin/python3 '
# alias py311='/opt/homebrew/bin/python3.11 '
trap 'exit' SIGHUP

# Save and share history across sessions
HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=100000

setopt HIST_IGNORE_DUPS       # Don't store duplicate commands
setopt HIST_FIND_NO_DUPS      # Don't show duplicates when searching
setopt INC_APPEND_HISTORY     # Save history incrementally
setopt SHARE_HISTORY          # Share history across terminals

# Prefix-based history search (↑ / ↓ after typing)
bindkey "^[[A" history-search-backward   # ↑
bindkey "^[[B" history-search-forward    # ↓

# poetry
# PATH and tool roots consolidated to ~/.zprofile for faster interactive shells
export ARTIFACTORY_USERNAME=vla.dunev@tomtom.com

alias term='open -a Terminal'
alias zfresh='exec zsh'
alias zsrc='source ~/.zshrc && echo "✅ .zshrc reloaded"'

#git

gs() {
  echo "🔍 Git Status:"
  git status
  # --short
  echo ""
  echo "📦 Repo: $(basename "$(git rev-parse --show-toplevel)")"
  echo "🌐 Remote: $(git remote get-url origin)"
  echo "🧑 Author: $(git config user.name) <$(git config user.email)>"
}

alias gadd='git add'
# alias gs='git status'
alias glfs='git lfs ls-files'
alias gsize='(git ls-files --others --exclude-standard && git diff --name-only) | sort -u | while IFS= read -r file; do
    if [ -f "$file" ] && [ $(du -m "$file" | cut -f1) -gt 42 ]; then
        echo "$file : $(du -h "$file" | cut -f1)"
    fi
done'
alias gpush='git push'
alias gurl='git config --get remote.origin.url'
alias gball='git branch --all'
alias gfet='git fetch --prune'
alias gf='git fetch --prune && git status -sb'

alias gcout='function _gco() { git checkout "$@"; }; _gco'
alias gcomm='function _gcm() { git commit -m "$@"; }; _gcm'

alias gex='function _gcm() { gh copilot explain "$@"; }; _gcm'

export PATH="$HOME/.local/bin:$PATH"
alias py='python'
alias py3='python3'


# pyenv (interactive init only)
# Path-level pyenv init moved to ~/.zprofile to avoid repeated path manipulation on each interactive shell.
export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
if command -v pyenv >/dev/null 2>&1; then
  # ensure pyenv bin is available in case a non-login shell skipped ~/.zprofile
  export PATH="$PYENV_ROOT/bin:$PATH"
  # interactive shell setup (functions, rehash, auto-switching via .python-version)
  eval "$(pyenv init -)"
  # keep virtualenv auto-activation (only run when pyenv is present)
  eval "$(pyenv virtualenv-init -)"
fi

# eval "$(direnv hook zsh)"


# # # Function to display the active virtual environment

# function prompt_virtualenv() {
#     if [[ -n "$VIRTUAL_ENV" ]]; then
#         echo "($(basename %F{013}$VIRTUAL_ENV)) "
#     fi
# }


# pyenv aliases
# alias pylist='pyenv virtualenvs'
alias pylist='pyenv versions'
alias pyact='function _pyact() { pyenv activate "$@"; }; _pyact'
alias pydeact='pyenv deactivate'
alias pyver='pyenv version'

# Run Databricks keepalive in the current terminal (no GUI scripting)
mcr_alive() {
  cd /Users/dunevv/WorkLocal/_AI_/HoudiniElf/tools_QGIS/dbQGIS || return
  # Load .env into this shell (optional but requested)
  if [ -f .env ]; then
    set -o allexport
    # shellcheck disable=SC1091
    source .env
    set +o allexport
  fi
  # Activate the project's virtualenv and run the keepalive
  # This will run in the same terminal so you can stop it with Ctrl+C
  source /Users/dunevv/WorkLocal/_AI_/HoudiniElf/.venv/bin/activate
  dotenv run -- python databricks_keepalive2.py -c /dev/null -i 500
}
alias caffeine='caffeinate -d'
alias iterm='open -a iTerm $*'
alias wake='wakeonlan 60:CF:84:BC:9F:1B'
alias allow='sudo xattr -rd com.apple.quarantine'


export GIT_EDITOR="code --wait"
# export OLLAMA_MODELS="/Volumes/exFAT/AI/Ollama/models"
export OLLAMA_MODELS="/Users/dunevv/WorkLocal/_GIT_/AI/Ollama/models"
export PYTORCH_ENABLE_MPS_FALLBACK=1

# # color prompt
# function set_prompt {
#   local blue=$'\e[38;2;76;167;248m'
#   local reset=$'\e[0m'
#   PROMPT="%{$blue%}%~ > %{$reset%}"
# }
# set_prompt


# export DIRENV_DISABLE_PROMPT=1

# Old Function to display the active virtual environment

function prompt_virtualenv() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "($(basename %F{013}$VIRTUAL_ENV)) "
    fi
}

# color prompt
function set_prompt {
  local blue=$'\e[38;2;76;167;248m'
  local reset=$'\e[0m'
  PROMPT="%{$blue%}%~ > %{$reset%}"
}
set_prompt

# # New Function to display the active virtual environment
# function prompt_virtualenv() {
#     if [[ -n "$VIRTUAL_ENV" ]]; then
#         echo "($(basename $VIRTUAL_ENV)) "
#     fi
# }

# # Color prompt with virtualenv
# function set_prompt {
#   local blue=$'\e[38;2;76;167;248m'
#   local reset=$'\e[0m'
#   PROMPT="$(prompt_virtualenv)%{$blue%}%~ > %{$reset%}"
# }
# set_prompt


# bun completions
[ -s "/Users/dunevv/.bun/_bun" ] && source "/Users/dunevv/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
# echo "source $(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" >> ${ZDOTDIR:-$HOME}/.zshrcsource /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
