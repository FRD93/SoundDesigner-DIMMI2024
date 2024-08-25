#!/usr/bin/env bash

echo "Running SoundDesigner"
echo "SoundDesigner - ©2024, Francesco Roberto Dani"

# # Linux Installation Process
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [[ ! -e "venv" ]]; then
                python3.11 -m venv venv
        fi
        source venv/bin/activate
        python graphics.py
fi
