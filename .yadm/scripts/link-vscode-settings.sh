if grep -iq microsoft /proc/version; then
  cp $HOME/.vscode-settings.json /mnt/c/Users/akmin/AppData/Roaming/Code/User/settings.json
  cp $HOME/.vscode-keybindings.json /mnt/c/Users/akmin/AppData/Roaming/Code/User/keybindings.json
else
  ln -s $HOME/.vscode-settings.json $HOME/.config/Code/User/settings.json
  ln -s $HOME/.vscode-keybindings.json $HOME/.config/Code/User/keybindings.json
fi
echo "Settings files linked"