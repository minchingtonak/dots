#!/bin/sh
### Created by ilsenatorov https://github.com/Mocktezuma/dotfiles/blob/master/.config/rofi/scripts/themeswitch.sh

WALLPAPERDIR=~/papes

if [ -z $@ ]
then
function get_themes()
{
    ls $WALLPAPERDIR
}
echo current; get_themes
else
    THEMES=$@
    if [ x"current" = x"${THEMES}" ]
    then
        exit 0
    elif [ -n "${THEMES}" ]
    then
        wallpaper "$WALLPAPERDIR/${THEMES}" > /dev/null
    fi
fi
