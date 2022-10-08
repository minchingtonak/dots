# https://github.com/popstas/zsh-command-time

# Modified by Alec Minchington (github:minchingtonak)

_command_time_preexec() {
  timer=${timer:-$SECONDS}
  export ZSH_COMMAND_TIME=""
}

_command_time_precmd() {
  if [ $timer ]; then
    timer_show=$(($SECONDS - $timer))
    if [ -n "$TTY" ] && [ $timer_show -ge ${ZSH_COMMAND_TIME_MIN_SECONDS:-3} ]; then
      export ZSH_COMMAND_TIME="$timer_show"
    fi
    unset timer
  fi
}

zsh-command-time() {
    if [ ! -z "$ZSH_COMMAND_TIME" ]; then
        printf "$1" "$ZSH_COMMAND_TIME"
    fi
}

precmd_functions+=(_command_time_precmd)
preexec_functions+=(_command_time_preexec)
