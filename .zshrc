# Use powerline
USE_POWERLINE="true"
# Source manjaro-zsh-configuration
if [[ -e /usr/share/zsh/manjaro-zsh-config ]]; then
  source /usr/share/zsh/manjaro-zsh-config
fi
if [[ -e /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh ]]; then
  source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
fi

# Prompt
autoload -Uz vcs_info
precmd() { vcs_info }
zstyle ':vcs_info:*' enable git
# zstyle ':vcs_info:git*' formats "(%b) %m%u%c"
# zstyle ':vcs_info:git*' actionformats "(%b) (%a) %m%u%c"
# https://github.com/ohmyzsh/ohmyzsh/blob/master/themes/apple.zsh-theme
zstyle ':vcs_info:*' check-for-changes true
zstyle ':vcs_info:*' unstagedstr '%F{red}*%f'   # display this when there are unstaged changes
zstyle ':vcs_info:*' stagedstr '%F{yellow}+%f'  # display this when there are staged changes
zstyle ':vcs_info:*' actionformats '%F{8}:%F{5}(%F{2}%b%F{3}|%F{1}%a%c%u%F{5})%f'
zstyle ':vcs_info:*' formats '%F{8}:%F{5}(%F{2}%b%c%u%F{5})%f'
setopt prompt_subst
# color test: %F{1}1 %F{2}2 %F{3}3 %F{4}4 %F{5}5 %F{6}6 %F{7}7 %F{8}8 %F{9}9
PROMPT='%F{4}%~%f${vcs_info_msg_0_}%{$reset_color%} %F{5}%Bλ%b%f '
RPROMPT='%(?..%B%F{3} ✗%? %f%b)'

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
HYPHEN_INSENSITIVE="true"

# Uncomment the following line to display red dots whilst waiting for completion.
COMPLETION_WAITING_DOTS="true"

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

export EDITOR='code'
export TERMINAL='alacritty'
export BROWSER='firefox'
export WORKSPACE="$HOME/workspace"

source $HOME/.bash_aliases

bindkey '^H' backward-delete-word
# bindkey -l will give you a list of existing keymap names
# bindkey -M <keymap> will list all the bindings in a given keymap
# ctrl + delete
bindkey '^[[3;5~' kill-word

# start in workspace unless this in an integrated vscode terminal
[ -z "$VSC" ] && ws

# Import colorscheme from 'wal' asynchronously
# &   # Run the process in the background.
# ( ) # Hide shell job control messages.
(cat ~/.cache/wal/sequences &)

PATH=~/.local/bin:$PATH
