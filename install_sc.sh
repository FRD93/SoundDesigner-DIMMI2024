#!/usr/bin/env bash

echo "Installing SuperCollider and SuperCollider-dependent code required by SoundDesigner"
echo "SoundDesigner - ©2024, Francesco Roberto Dani"
mkdir tmp
cd tmp || exit

# # Linux Installation Process
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # # Install unzip and SuperCollider
        sudo apt-get update
        sudo apt-get install unzip
        sudo apt-get install supercollider-ide
        # # Install SC3-PlugIns
        wget "https://github.com/supercollider/sc3-plugins/releases/download/Version-3.13.0/sc3-plugins-3.13.0-Linux-x64.zip" .
        unzip sc3-plugins-3.13.0-Linux-x64.zip
        sudo mv lib /usr/share/SuperCollider/Extensions/
        sudo mv share /usr/share/SuperCollider/Extensions/
        # # Install WSlib
        git clone https://github.com/supercollider-quarks/wslib.git
        sudo mv wslib/wslib-classes /usr/share/SuperCollider/Extensions/
        # # Install FRDSClib
        git clone https://github.com/FRD93/FRDSClib.git
        sudo mv FRDSClib /usr/share/SuperCollider/Extensions/
        # # Complete Installation of SuperCollider dependent code
        echo "Finishing..."
        /usr/bin/sclang ../src/supercollider/setup.scd

# # MacOS Installation Process
elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Working OS: OS-X"
        echo "Installing..."
        # Install unzip and SuperCollider
        brew install unzip
        brew install --cask supercollider
        # Install SC3-PlugIns
        wget "https://github.com/supercollider/sc3-plugins/releases/download/Version-3.13.0/sc3-plugins-3.13.0-macOS.zip" .
        unzip "./sc3-plugins-3.13.0-macOS.zip"
        mv "./sc3-plugins-3.13.0-macOS" "/Library/Application Support/SuperCollider/Extensions/"
        # # Install WSlib
        git clone https://github.com/supercollider-quarks/wslib.git
        mv "./wslib/wslib-classes" "/Library/Application Support/SuperCollider/Extensions/"
        # Install FRDSCLib
        git clone https://github.com/FRD93/FRDSClib.git
        mv "./FRDSCLib" "/Library/Application Support/SuperCollider/Extensions/"
        # # Complete Installation of SuperCollider dependent code
        echo "Finishing..."
        /applications/Supercollider.app/Contents/MacOS/sclang "../src/supercollider/setup.scd"

# # TODO: Windows Installation Process
fi

echo "Cleaning..."
cd .. || exit
rm -rf tmp
