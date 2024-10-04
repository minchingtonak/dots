#!/bin/sh

get_options() {
    # list names of audio sources (Description is the human readable name)
    # grep -n '' adds index numbers to each line
    pactl list sources | grep 'Description: ' | cut -d' ' -f2- | grep -n ''
}

set_current_mic() {
    # strip the index from the front of the user's choice
    desc=$(echo "$1" | cut -d':' -f2-)
    name=$(pactl list sources | grep -1 "$desc" | grep 'Name: ' | cut -d' ' -f2-)

    echo "$name" >/tmp/current-source-name
}

main() {
    # get choice from rofi
    choice=$( (get_options) | rofi -dmenu -i -fuzzy -p "source")

    # if choice is not empty (will be empty if user presses esc)
    if [ -n "$choice" ]; then
        set_current_mic "$choice"
    fi
}

main &

exit 0
