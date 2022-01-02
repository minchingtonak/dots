alias caen='ssh $UNIQNAME@login.engin.umich.edu'
alias ws='cd $WORKSPACE'
alias dl='cd $HOME/Downloads'
alias tmp='cd /tmp'
alias weather='curl http://wttr.in/ann_arbor'
alias l='ls -a --color=tty'
alias ll='ls -alhF --color=tty'
alias lll='du -h --max-depth=1 | sort -hr'
llf() { ll | awk 'NR > 1 && !/^d/ { printf "%s\t%s\n",$5,$9 }' | sort -hr; }
alias la='ls -A --color=tty'
alias aliases="$EDITOR ~/.bash_aliases"
alias bashrc="$EDITOR ~/.bashrc"
alias zshrc="$EDITOR ~/.zshrc"
alias act='source env/bin/activate'
alias deact='deactivate'
alias batthresh='sudo $EDITOR /etc/tlp.conf'
mk() { mkdir -p $1 && cd $1; }
mknodeenv() {
  python3 -m venv env &&
  act &&
  pip install nodeenv &&
  nodeenv --python-virtualenv env &&
  deact && act
}
locate() { find . -name "$1" 2> /dev/null; }
alias scheme='plt-r5rs'
alias vsc='code .'

# yadm
alias y='yadm'
alias ya='y add'
alias yaa='y add -u'
alias yc='y commit'
alias ycm='y commit -m'
alias yco='y checkout'
alias yb='y branch'
alias yp='y push'
alias yrh='y reset HEAD'
alias yd='y diff'
alias ydt='y difftool'
alias yl='y log --oneline --decorate --graph'
alias ypom='yp origin master'
alias yst='y status'
alias yr='y remote'

# git
alias gst='git status'
alias gl='git log --oneline --decorate --graph'
alias glog='git log'
alias ga='git add'
alias gaa='git add -A'
alias gr='git remote'
alias gp='git push'
alias gpl='git pull'
alias gpom='gp origin master'
alias gco='git checkout'
alias gb='git branch'
alias gc='git commit'
alias gd='git diff'
alias gdt='git difftool'
