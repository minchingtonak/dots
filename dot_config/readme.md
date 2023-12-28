
## official (o-fish-all) linux issues anti-frustration guide


### wifi isn't working

This surfaces as the wifi card showing up in `lspci` but not in `nmcli d` or `ip addr`. It happens because of windows' fast startup feature which is enabled by default. Basically shutting down your computer from windows won't always fully shut down the computer, and sometimes windows will keep hold of some devices including the wifi card. This means that linux can't use the wifi card unless windows relinquishes control of it. To fix, disable fast startup in windows.
