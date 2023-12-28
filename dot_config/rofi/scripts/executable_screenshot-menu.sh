#!/bin/sh
# Modified from https://github.com/Keyitdev/dotfiles/blob/v3/scripts/rofi-screenshot

get_options() {
  echo "  Selected area screenshot"
  echo "  Full screen screenshot (1s delay)"
  echo "  Selected area video"
  echo "  Full screen video (1s delay)"
  echo "  Record audio (microphone)"
  echo "  Record audio (desktop)"
  echo "  Selected area video with audio (microphone)"
  echo "  Full screen video with audio (microphone) (1s delay)"
  echo "  Stop Recording"
}

main() {

  # get choice from rofi
  choice=$( (get_options) | rofi -dmenu -i -fuzzy -p "")


  # run the selected command
  case $choice in
  '  Selected area screenshot')
    screenshot -sa
    ;;
  '  Full screen screenshot (1s delay)')
    sleep 1
    screenshot -sf
    ;;
  '  Selected area video')
    screenshot -va
    ;;
  '  Full screen video (1s delay)')
    sleep 1
    screenshot -vf
    ;;
  '  Record audio (microphone)')
    screenshot -am
    ;;
  '  Record audio (desktop)')
    screenshot -ad
    ;;
  '  Selected area video with audio (microphone)')
    screenshot -vaam
    ;;
  '  Full screen video with audio (microphone) (1s delay)')
    sleep 1
    screenshot -vfam
    ;;
  '  Stop Recording')
    screenshot -s
    ;;
  esac

  # done
  set -e
}

main &

exit 0