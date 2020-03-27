#!/usr/bin/env bash
set -Eeuxo pipefail

if grep -iq microsoft /proc/version; then
  cp $HOME/.config/Code/User/settings.json /mnt/c/Users/akmin/AppData/Roaming/Code/User/settings.json
  cp $HOME/.config/Code/User/keybindings.json /mnt/c/Users/akmin/AppData/Roaming/Code/User/keybindings.json
fi
echo "Settings files linked"