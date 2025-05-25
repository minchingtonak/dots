#!/bin/bash
# Wrapper script to run voice transcriber with virtual environment

VENV_PATH="$HOME/.local/share/voice_transcriber_env"
SCRIPT_PATH="$HOME/.local/bin/voice_transcriber.py"

# Activate virtual environment and run the script
source "$VENV_PATH/bin/activate"
python "$SCRIPT_PATH" "$@"
deactivate
