#!/bin/sh
# Modified from https://github.com/Keyitdev/dotfiles/blob/v3/scripts/rofi-powermenu

get_options() {
  echo " Poweroff"
  echo " Reboot"
  echo " Hibernate"
  echo " Lock"
  echo " Log out"
}

main() {

  # get choice from rofi
  choice=$( (get_options) | rofi -dmenu -i -fuzzy -p "" )

  # run the selected command
  case $choice in
  ' Poweroff')
    systemctl poweroff
    ;;
  ' Reboot')
    systemctl reboot
    ;;
  ' Hibernate')
    systemctl hibernate
    ;;
  ' Lock')
    lockscreen
    ;;
  ' Log out')
    i3-msg exit
    ;;
  esac

  # done
  set -e
}

main &

exit 0