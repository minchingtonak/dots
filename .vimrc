set nocompatible
call plug#begin('~/.vim/plugged')

Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'

Plug 'itchyny/lightline.vim'

Plug 'tpope/vim-surround'

Plug 'scrooloose/nerdtree'
Plug 'Xuyuanp/nerdtree-git-plugin'

Plug 'tpope/vim-fugitive'

Plug 'drewtempelmeyer/palenight.vim'

Plug 'Valloric/YouCompleteMe', { 'do': './install.py --clang-completer' }

Plug 'jiangmiao/auto-pairs'

Plug 'rhysd/vim-clang-format'

call plug#end()

"============General Config=============
set backspace=indent,eol,start  "Allow backspace in insert mode
set history=1000                "Store lots of :cmdline history

" This makes vim act like all other editors, buffers can
" exist in the background without being in a window.
" http://items.sjbach.com/319/configuring-vim-right
set hidden

"turn on syntax highlighting
syntax on

" Better search
set hlsearch
set incsearch

autocmd FocusLost * silent! wa " Automatically save file

set scrolloff=5 " Keep 5 lines below and above the cursor

set cursorline

" ================ Swapfile config ==================
" No swapfiles
"set noswapfile
"set nobackup
"set nowb

set directory^=$HOME/.vim/swaps// " Keep all swapfiles in central dir

" ================ Persistent Undo ==================
" Keep undo history across sessions, by storing in file.
" Only works all the time.
if has('persistent_undo')
  silent !mkdir ~/.vim/backups > /dev/null 2>&1
  set undodir=~/.vim/backups
  set undofile
endif

" ================ Indentation ======================
set autoindent
set smartindent
set smarttab
set shiftwidth=2
set softtabstop=2
set tabstop=2
set expandtab

" =============== Theming ===========================
"echo grep -q Microsoft /proc/version

colorscheme palenight
" Lightline config for palenight
let g:lightline = {
      \ 'colorscheme': 'palenight',
      \ 'palenight_terminal_italics': 1,
      \ }
" Italics for my favorite color scheme
let g:palenight_terminal_italics=1

set number
set laststatus=2
set noshowmode
set background=dark
set gcr=a:blinkon0              "Disable cursor blink
set visualbell                  "No sounds
set autoread                    "Reload files changed outside vim

syntax enable

if has("gui_running")
  "tell the term has 256 colors
  set t_Co=256
end

"For Neovim > 0.1.5 and Vim > patch 7.4.1799 < https://github.com/vim/vim/commit/61be73bb0f965a895bfb064ea3e55476ac175162 >
"Based on Vim patch 7.4.1770 (`guicolors` option) < https://github.com/vim/vim/commit/8a633e3427b47286869aa4b96f2bfc1fe65b25cd >
" < https://github.com/neovim/neovim/wiki/Following-HEAD#20160511 >
if (has("termguicolors"))
  set termguicolors
endif

" =============== Remaps ============================
map ; :
noremap ;; ;
" d = delete line
" leader d = cut
"nnoremap x "_x
"nnoremap d "_d
"nnoremap D "_D
"vnoremap d "_d

"nnoremap <leader>d ""d
"nnoremap <leader>D ""D
"vnoremap <leader>d ""d

let mapleader = ","
let g:mapleader = ","

" Auto indent pasted text
nnoremap p p=`]<C-o>
nnoremap P P=`]<C-o>

" Autoformatting
" map to <Leader>cf in C++ code
autocmd FileType c,cpp,objc nnoremap <buffer><Leader>cf :<C-u>ClangFormat<CR>
autocmd FileType c,cpp,objc vnoremap <buffer><Leader>cf :ClangFormat<CR>

" Easy line insertion
map <Enter> o<ESC>
map <S-Enter> O<ESC>

" =============== NERDTree config ===================
map <C-O> :NERDTreeToggle<CR>
"Open NERDTree, NERDTreeFind on current file
nnoremap <Leader>f :NERDTreeToggle<Enter>
nnoremap <silent> <Leader>v :NERDTreeFind<CR>

"Open NERDTree when starting vim w/ no clargs
autocmd StdinReadPre * let s:std_in=1
autocmd VimEnter * if argc() == 0 && !exists("s:std_in") | NERDTree | endif

"Close NERDTree if last window open
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTree") && b:NERDTree.isTabTree()) | q | endif

let NERDTreeQuitOnOpen = 1
let NERDTreeMinimalUI = 1
let NERDTreeDirArrows = 1
let NERDTreeAutoDeleteBuffer = 1
let NERDTreeShowHidden = 1

" =============== Autoformatter config ==============
let g:clang_format#code_style = 'llvm'
"let g:clang_format#style_options = {
"      \ "AllowShortIfStatementsOnASingleLine" : "true",
"      \ "ColumnLimit" : 100,
"      \ "IndentWidth" : 4,
"      \ "KeepEmptyLinesAtTheStartOfBlocks" : "false",
"      \ "MaxEmptyLinesToKeep" : 1,
"      \ "PointerAlignment" : "PAS_Right",
"      \ "SortUsingDeclarations" : "true",
"      \ "SpaceBeforeRangeBasedForLoopColon" : "true"}

let g:clang_format#style_options = {
      \ "IndentWidth" : 4,
      \ "ColumnLimit" : 100}

let g:clang_format#detect_style_file = 0

" =============== Misc ==============================
" vimplug auto install
if empty(glob('~/.vim/autoload/plug.vim'))
  silent !curl -fLo ~/.vim/autoload/plug.vim --create-dirs
        \ https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
  autocmd VimEnter * PlugInstall --sync | source $MYVIMRC
endif

let g:ycm_global_ycm_extra_conf = '~/.ycmconf.py' " YouCompleteMe default C/C++ compile flags

if &diff
  highlight! link DiffText MatchParen
endif

" Left here for later use
if (match(system("cat /proc/version"), "Microsoft") != -1)
  " If we're in WSL
endif
