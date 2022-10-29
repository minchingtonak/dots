# Prompt setup
source ~/.config/zsh/shrink-path.zsh
shrink-path-toggle() {
  zstyle -t ':prompt:shrink_path' expand \
    && zstyle -d ':prompt:shrink_path' expand \
    || zstyle ':prompt:shrink_path' expand true
  zle reset-prompt
}
zle -N shrink-path-toggle
# Key binding to ALT+SHIFT+S
bindkey "^[S" shrink-path-toggle

source ~/.config/zsh/command-time.zsh
ZSH_COMMAND_TIME_MIN_SECONDS=3

autoload -Uz vcs_info
precmd() { vcs_info }
zstyle ':vcs_info:*' enable git
# https://github.com/ohmyzsh/ohmyzsh/blob/master/themes/apple.zsh-theme
zstyle ':vcs_info:*' check-for-changes true
zstyle ':vcs_info:*' unstagedstr '%F{red}*%f'   # display this when there are unstaged changes
zstyle ':vcs_info:*' stagedstr '%F{yellow}+%f'  # display this when there are staged changes
zstyle ':vcs_info:*' actionformats '%F{8}:%F{5}(%F{2}%b%F{3}|%F{1}%a%c%u%F{5})%f'
zstyle ':vcs_info:*' formats '%F{8}:%F{5}(%F{2}%b%c%u%F{5})%f'
setopt prompt_subst
# color test: %F{1}1 %F{2}2 %F{3}3 %F{4}4 %F{5}5 %F{6}6 %F{7}7 %F{8}8 %F{9}9
PROMPT='%(!.# .)%F{4}$(shrink_path -t -1)%f${vcs_info_msg_0_}%{$reset_color%} %F{5}%Bλ%b%f '
RPROMPT='%(?..%B%F{3} ✗ %? %f%b)$(zsh-command-time "took %%F{2}%%B%ds%%b%%f")'
