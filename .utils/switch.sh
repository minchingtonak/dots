yadm checkout $([ "$(yadm branch | grep \* | cut -d ' ' -f2)" = "master" ] && echo "old" || echo "master")

prev="$(cat .yadm/prev_shell)"
echo $SHELL > .yadm/prev_shell
chsh -s "$prev"
echo "Configuration switched. Please log out and log back in."
