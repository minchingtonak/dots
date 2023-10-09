# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/.local/bin" ]; then
    case "$PATH" in
      (*/.local/bin*)
        echo -n '' >/dev/null
        ;;
      (*)
        export PATH="$HOME/.local/bin:$PATH"
        ;;
    esac
fi

export EDITOR='code'
export TERMINAL='alacritty'
export BROWSER='firefox'
export WORKSPACE="$HOME/workspace"
