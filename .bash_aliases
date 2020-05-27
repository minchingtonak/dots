alias caen='ssh $UNIQNAME@login.engin.umich.edu'
alias ws='cd $WORKSPACE'
alias dl='cd $HOME/Downloads'
alias tmp='cd /tmp'
alias windows='cd /mnt/c/Users/'
alias weather='curl http://wttr.in/ann_arbor'
alias l='ls -a --color=tty'
alias ll='ls -alhF --color=tty'
alias lll='du -h --max-depth=1 | sort -hr'
llf() { ll | awk 'NR > 1 && !/^d/ { printf "%s\t%s\n",$5,$9 }' | sort -hr }
alias la='ls -A --color=tty'
alias gl='glog'
alias gpom='gp origin master'
alias exp="explorer.exe ."
alias aliases="$EDITOR ~/.bash_aliases"
alias bashrc="$EDITOR ~/.bashrc"
alias zshrc="$EDITOR ~/.zshrc"
alias act='source env/bin/activate'
alias deact='deactivate'
mk() { mkdir -p $1 && cd $1 }
locate() { sudo find . -name "$1" 2> /dev/null }
snewl() {
  if grep -q 'SPACESHIP_PROMPT_SEPARATE_LINE=true' ~/.zshrc; then
    sed -i -e 's/SPACESHIP_PROMPT_SEPARATE_LINE=true/SPACESHIP_PROMPT_SEPARATE_LINE=false/' ~/.zshrc
  else
    sed -i -e 's/SPACESHIP_PROMPT_SEPARATE_LINE=false/SPACESHIP_PROMPT_SEPARATE_LINE=true/' ~/.zshrc
  fi
  tmp="$(pwd)"
  source ~/.zshrc
  cd $tmp
}
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
