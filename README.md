# SoundDesigner-DIMMI2024
This repository contains a reduced GPL version of SoundDesigner, released for DIMMI conference held in Trento (IT) in 2024.

# Installation (Linux and macOS)

PLEASE downlaod and install Ambisonic Tool Kit separately.

Follow the instructions below to install SoundDesigner into your system. Currently supported platforms are MacOS and Linux.

## SuperCollider and related

Run "install_sc.sh" file for an automated installation process of SuperCollider and all the SC-related code needed by SoundDesigner to work.
- Note: you may need to execute before to allow execution of file.
```
cd SoundDesigner/
sudo chmod +x install_sc.sh
./install_sc.sh
```

## Building From Source

Run "build_from_source.sh" file to build from source SoundDesigner.
- Note: you may need to execute before to allow execution of file.
```
cd SoundDesigner/
sudo chmod +x build_from_source.sh
./build_from_source.sh
```

# Intallation (Windows)

For Windows, you have to manually install dependencies and directly run the main SoundDesigner python file within a python3.11 venv, so do the following:
- Install SuperCollider and sc3-plugins
- Install FRDSCLib (can be found at: )