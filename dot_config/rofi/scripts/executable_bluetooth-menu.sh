#!/bin/sh

get_options() {
  bluetoothctl devices Paired | cut -d ' ' -f 2-
}

connect_or_disconnect() {
  device=$(echo "$1" | cut -d ' ' -f 1)

  if bluetoothctl info "$device" | grep -iq 'Connected: yes'; then
    bluetoothctl disconnect "$device"
  else
    bluetoothctl connect "$device"
  fi
}

main() {
  # get choice from rofi
  choice=$( (get_options) | rofi -dmenu -i -fuzzy -p "device")

  # if choice is not empty (will be empty if user presses esc)
  if [ -n "$choice" ]; then
    connect_or_disconnect "$choice"
  fi
}

main &

exit 0
