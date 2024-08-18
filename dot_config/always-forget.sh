#!/hint/bash
# shellcheck disable=SC2317

exit 7 # just exit if somehow I manage to execute this

#
# my unix cheat sheet
#
# inspiration: https://github.com/awdeorio/dotfiles/blob/57004769418a8c16d816fae951a7d2f023fcec0f/.always_forget.txt
#

# package management
pacman -Runs PACKAGE # remove a package, all it's unnecessary dependencies, any unneeded packages, and any configuration files
pacman -Qm           # list all installed AUR packages
pacman -Ql PACKAGE   # list all files owned by a package
pacman -Qo FILE      # find the package that owns a file
pacman -Sc           # remove uninstalled package tarballs from cache
pacman -Scc          # remove all package tarballs from cache

aura -L          # view the pacman log
aura -Li PACKAGE # view log info for a package

aura -Cl   # list cache contents
aura -Cm   # list packages that don't have a tarball in the cache
aura -Ct   # delete invalid tarballs from the cache
aura -Cc N # save the most recent N versions of a package

aura -B         # save global package state
aura -Bl        # list all saved package snapshots
aura -Br        # restore from a saved state. downgrades upgraded packages, removes recently installed
aura -Bc NUMBER # save the most recent N package snapshots

aura -As PACKAGE             # search the AUR for packages
aura -As --abc PACKAGE       # search the AUR for packages, sorted alphabetically
aura -Ai PACKAGE             # display info about a package
aura -Ap PACKAGE             # print a package's PKGBUILD
aura -A PACKAGE              # install a package from the AUR
aura -Aa PACKAGE             # install a package from the AUR and remove makedeps
aura -Ac PACKAGE             # delete a package's build directory after the built tarball has been copied
aura -A PACKAGE --hotedit    # edit PKGBUILD before installing
aura -A PACKAGE --shellcheck # run shellcheck on PKGBUILD before installing
aura -Ayu                    # refresh and upgrade installed AUR packages
aura -Ayuka                  # upgrade all AUR packages, show PKGBUILD diffs, and remove unneeded makedeps after installation

aura -O  # display orhpaned packages
aura -Oj # uninstall all orphaned packages
