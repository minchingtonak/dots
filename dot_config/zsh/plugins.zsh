export FZF_CTRL_T_OPTS="--preview '(highlight -O ansi -l {} 2> /dev/null || cat {} || tree -C {}) 2> /dev/null | head -200'"

export FZF_CTRL_R_OPTS="
  --preview 'echo {}' --preview-window up:3:hidden:wrap
  --bind 'ctrl-/:toggle-preview'
  --bind 'ctrl-y:execute-silent(echo -n {2..} | xclip -selection clipboard)+abort'
  --color header:italic
  --header 'ctrl-Y to copy to clipboard, ctrl-/ to open preview window for long commands'"

export FZF_ALT_C_OPTS="--preview 'tree -C {} | head -200'"

plugins=(
    ~/.config/zsh/prompt.zsh
    /usr/share/fzf/completion.zsh
    /usr/share/fzf/key-bindings.zsh # ctrl-t=show file picker, ctrl-r=show command history picker, alt-c=show dir picker
    /usr/share/zsh/plugins/zsh-autopair/autopair.zsh
    /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
    /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
)

for p in $plugins; do
    if [[ -e $p ]]; then
        source $p
    else
        echo "(warning) plugin $p was not found"
    fi
done
