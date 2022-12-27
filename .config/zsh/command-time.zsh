# https://github.com/popstas/zsh-command-time

# Modified by Alec Minchington (github:minchingtonak)

_command_time_preexec() {
  millis=$(date +%s%3N)
  timer=${timer:-$millis}
  export ZSH_COMMAND_TIME=""
}

_command_time_precmd() {
  if [ $timer ]; then
    millis=$(date +%s%3N)
    timer_show=$(( ($millis - $timer) / 1000.0 ))
    zmodload zsh/mathfunc
    if [ -n "$TTY" ] && [ $(( int($timer_show) )) -ge ${ZSH_COMMAND_TIME_MIN_SECONDS:-3} ]; then
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
