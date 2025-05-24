# Install guide

1. configure ssh key for github
2. init dotfiles: `chezmoi init --apply git@github.com:minchingtonak/dots.git`
3. DO NOT reboot before installing packages
4. run `install_packages`. SKIP INFORMANT INSTALL WHEN PROMPTED
5. install informant: `yay -S informant && usermod -aG informant akmin`
6. reboot
7. set up syncthing to get access to passwords
8. clone wallpapers: `cd ~ && git clone git@github.com:minchingtonak/wp.git`
9. run `wallpaper`
10. run `install_spicetify`
11. run `install_vesktop` if using mute bind
