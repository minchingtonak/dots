alias caen='ssh $UNIQNAME@login.engin.umich.edu'
alias ws='cd $WORKSPACE'
alias dl='cd $HOME/Downloads'
alias tmp='cd /tmp'
alias weather='curl http://wttr.in/ann_arbor'
alias l='ls -a --color=tty'
alias ll='ls -alhF --color=tty'
alias lll='du -h --max-depth=1 | sort -hr'
llf() { ll | awk 'NR > 1 && !/^d/ { printf "%s\t%s\n",$5,$9 }' | sort -hr }
alias la='ls -A --color=tty'
alias aliases="$EDITOR ~/.bash_aliases"
alias bashrc="$EDITOR ~/.bashrc"
alias zshrc="$EDITOR ~/.zshrc"
alias act='source env/bin/activate'
alias deact='deactivate'
alias batthresh='sudo vim /etc/tlp.conf'
mk() { mkdir -p $1 && cd $1 }
mknodeenv() {
  python3 -m venv env &&
  act &&
  pip install nodeenv &&
  nodeenv --python-virtualenv env &&
  deact && act
}
locate() { find . -name "$1" 2> /dev/null }
y() { yadm $@ }
ya() { y add $@ }
yc() { y commit $@ }
ycm() { y commit -m $@ }
yco() { y checkout $@ }
yb() { y branch $@ }
yp() { y push $@ }
yrh() { y reset HEAD $@ }
yd() { y diff $@ }
ydt() { y difftool $@ }
yl() { y log --oneline --decorate --graph }
alias ypom="yp origin master"
alias yst="y status"
alias scheme="plt-r5rs"

# git
alias gst='git status'
alias gl='git log --oneline --decorate --graph'
alias glog='git log'
alias ga='git add'
alias gr='git remote'
alias gp='git push'
alias gpl='git pull'
alias gpom='gp origin master'
alias gco='git checkout'
alias gb='git branch'
alias gc='git commit'
