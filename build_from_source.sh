#!/usr/bin/env bash

echo "Installing SoundDesigner"
echo "SoundDesigner - ©2024, Francesco Roberto Dani"

# # Linux Installation Process
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # sudo apt-get install python3.11
        if [[ ! -e "venv" ]]; then
                python3.11 -m venv venv
        fi
        source venv/bin/activate
        pip install -r requirements.txt
        python -m PyInstaller SoundDesigner.spec
        echo "Working OS: $OSTYPE"
        echo "Installing..."
        python -m PyInstaller SoundDesigner.spec

# # MacOS Installation Process
elif [[ "$OSTYPE" == "darwin"* ]]; then
        # brew install python3.11
        if [[ ! -e "venv" ]]; then
                python3.11 -m venv venv
        fi
        source venv/bin/activate
        pip install -r requirements.txt
        python -m PyInstaller SoundDesigner.spec
        if [[ "$OSTYPE" == *"arm64"* ]]; then
                echo "Working OS: $OSTYPE"
                echo "Installing..."
                arch -arm64 python -m PyInstaller SoundDesigner.spec
        else
                echo "Working OS: $OSTYPE"
                echo "Installing..."
                python -m PyInstaller SoundDesigner.spec
        fi

# # TODO: Windows Installation Process
fi
deactivate
echo "Done. You can find the installed application in SoundDesigner/dist/SoundDesigner/"
