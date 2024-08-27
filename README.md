# SoundDesigner-DIMMI2024
By Francesco Roberto Dani (https://www.francesco-dani.com). This repository contains a reduced GPL version of SoundDesigner, released for the article "SoundDesigner: A Framework for Assisted Sound Composition" presented at DIMMI conference held in Trento (IT) in 2024.


# Installation

## Linux and macOS

Follow the instructions below to install SoundDesigner into your system. Currently supported platforms are MacOS and Linux.
![Video Demo](tutorials/installation/01%20-%20Installation%20Linux%20-%20cut.gif)


### SuperCollider and related

Run "install_sc.sh" file for an automated installation process of SuperCollider and all the SC-related code needed by SoundDesigner to work.
- Note: you may need to execute before to allow execution of file.
```
cd SoundDesigner/
sudo chmod +x install_sc.sh
./install_sc.sh
```

### Building From Source

Run "build_from_source.sh" file to build from source SoundDesigner.
- Note: you may need to execute before to allow execution of file.
```
cd SoundDesigner/
sudo chmod +x build_from_source.sh
./build_from_source.sh
```

# Installing manually

Follow the Windows instructions for a manual installation of SoundDesigner within your system.

## Windows

For Windows, you have to manually install dependencies and directly run the main SoundDesigner python file within a python3.11 venv, so do the following:
- Install SuperCollider and sc3-plugins
- Install FRDSCLib (can be found at https://github.com/FRD93/FRDSClib)
- Install python3.11, create a venv and install requirements ```pip install -r requirements.txt```
- Run (from inside the venv) ```python graphics.py```


# Configuration

## Ambisonic Tool Kit

PLEASE download and install Ambisonic Tool Kit for sc3 along with ATK Kernels separately (https://github.com/ambisonictoolkit/atk-sc3).
![Video Demo](tutorials/installation/02%20-%20ATK%20Installation%20Linux.gif)


## Setting up config.ini file

In this version, SoundDesigner configuration must be made manually. Please review the ```/src/config.ini``` file to check the correctness of all the paths and the first-time-boot hardware_device_name.
![Video Demo](tutorials/installation/03%20-%20SoundDesigner%20Configuration.gif)

# Usage

## Run the application

If you built SoundDesigner from source, you can run the executable located at ```SoundDesigner-DIMMI2024/dist/SoundDesigner/_internal/SoundDesigner```

## Manually run SoundDesigner

If you manually installed SoundDesigner within your system, you can manually run SoundDesigner with: 
```
cd SoundDesigner-DIMMI2024
source venv/bin/activate
cd src
python graphics.py
```
![Video Demo](tutorials/installation/04%20-%20SoundDesigner%20Usage.gif)
