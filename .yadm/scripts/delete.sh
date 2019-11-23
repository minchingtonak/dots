#!/bin/bash

printf "Are you sure you want to remove the dotfiles repo? [Y/n] "
read response
if [[ "$response" =~ [^Yy] ]]; then
        echo "Exiting"
        exit
fi

chsh -s "$(cat ~/.yadm/orig_shell)"
yadm checkout old
rm -rf ~/.yadm ~/.oh-my-zsh ~/gdb-dashboard ~/.utils
echo "Logout and log back in to see changes"