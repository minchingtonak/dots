# contains custom preambles for specific terminal instances (llm, calculator, etc)

if [ "${LLM}" = "true" ]; then
    setopt SHARE_HISTORY

    mkdir -p /tmp/llm
    export WORKSPACE=/tmp/llm

    export HISTFILE="$HOME/.llm_history"

    alias q='llm -t question'
    alias chat='llm chat -t chat'
fi
