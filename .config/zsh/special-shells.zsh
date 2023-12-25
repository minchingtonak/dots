# contains custom preambles for specific terminal instances (llm, calculator, etc)

if [ "${LLM}" = "true" ]; then
    mkdir -p /tmp/llm
    export WORKSPACE=/tmp/llm
fi
