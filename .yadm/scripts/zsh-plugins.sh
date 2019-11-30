DIR=${ZSH_CUSTOM:-~/.oh-my-zsh/custom}

# zsh-syntax-highlighting
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git $DIR/plugins/zsh-syntax-highlighting

# zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-autosuggestions $DIR/plugins/zsh-autosuggestions

# fzf-zsh
git clone https://github.com/junegunn/fzf.git $DIR/plugins/fzf
$DIR/plugins/fzf/install --bin

git clone https://github.com/Treri/fzf-zsh.git $DIR/plugins/fzf-zsh

# spaceship custom zsh prompt
git clone https://github.com/denysdovhan/spaceship-prompt.git $DIR/plugins/spaceship-prompt
ln -s $DIR/plugins/spaceship-prompt/spaceship.zsh-theme $DIR/themes/spaceship.zsh-theme

