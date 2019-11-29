alias caen='ssh akminch@login.engin.umich.edu'
alias ws='cd $HOME/workspace'
alias weather='curl http://wttr.in/ann_arbor'
alias l="ls -a --color=tty"
alias ll='ls -alhF --color=tty'
alias la='ls -A --color=tty'
alias gl='git log --graph --full-history --all --color \
  --pretty=format:"%x1b[31m%h%x09%x1b[32m%d%x1b[0m%x20%s"'
alias exp="explorer.exe ."
alias aliases="$EDITOR ~/.bash_aliases"
y() { yadm $@; }
ya() { y add $@; }
yc() { y commit $@; }
ycm() { y commit -m $@; }
yp() { y push $@; }
yrh() { y reset HEAD $@; }
yd() { y diff $@; }
ydt() { y difftool $@; }
yl() { y log --graph --full-history --all --color \
  --pretty=format:"%x1b[31m%h%x09%x1b[32m%d%x1b[0m%x20%s" }
alias yst="y status"
