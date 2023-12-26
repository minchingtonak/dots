if [[ -e /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh ]]; then
  source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
fi

source ~/.config/zsh/prompt.zsh

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
HYPHEN_INSENSITIVE="true"

# Uncomment the following line to display red dots whilst waiting for completion.
COMPLETION_WAITING_DOTS="true"

# set window title to last command name + working directory
preexec() { SHELL_PREV_CMD=$1;print -Pn "\e]0;$1 - $(shrink_path -t -1)\a" }
# set window title after command in case we changed directories (cd)
promptcmd() { print -Pn "\e]0;${SHELL_PREV_CMD-New Shell} - $(shrink_path -t -1)\a"; }
precmd_functions+=(promptcmd)

ex() {
  if [ -f $1 ] ; then
    case $1 in
      *.tar.bz2)   tar xjf $1   ;;
      *.tar.gz)    tar xzf $1   ;;
      *.bz2)       bunzip2 $1   ;;
      *.rar)       unrar x $1   ;;
      *.gz)        gunzip $1    ;;
      *.tar)       tar xf $1    ;;
      *.tbz2)      tar xjf $1   ;;
      *.tgz)       tar xzf $1   ;;
      *.zip)       unzip $1     ;;
      *.Z)         uncompress $1;;
      *.7z)        7z x $1      ;;
      *)           echo "'$1' cannot be extracted via ex()" ;;
    esac
  else
    echo "'$1' is not a valid file"
  fi
}

# User configuration
export HISTFILE="$HOME/.zsh_history"
export HISTSIZE=1000000000
export SAVEHIST=1000000000
setopt EXTENDED_HISTORY

PATH=~/.local/bin:$PATH

# env var and PATH setup
source ~/.profile

source $HOME/.bash_aliases

# invoke cat with no args and enter a key to get its keycode
# bindkey -l will give you a list of existing keymap names
# bindkey -M <keymap> will list all the bindings in a given keymap
bindkey "^[[1;5C" forward-word # ctrl + right
bindkey "^[[1;5D" backward-word # ctrl + left
bindkey '^H' backward-delete-word # ctrl + backspace
bindkey '^[[3~' delete-char # delete
bindkey '^[[3;5~' kill-word # ctrl + delete

# tab completion
# bindkey '^I' autosuggest-accept
bindkey '\t\t' autosuggest-accept

# outer parens are to silence control messages
((cat ~/.cache/wal/sequences && dispatch-shell-colors) &)
source ~/.config/zsh/special-shells.zsh

# nvm setup
export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm

# pyenv setup
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# start in workspace unless this in an integrated vscode terminal
[ -z "$VSC" ] && ws
