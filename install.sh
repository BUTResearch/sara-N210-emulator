#!/bin/bash

pip install ping3
sudo apt -y install packetsender

dir=$PWD
home_dir=${HOME}


cat > "${home_dir}/Desktop/NB-IoT Emulator.desktop" <<EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=NB-IoT Emulator
Comment=
Exec=${dir}/start_emulator.sh
Icon=${dir}/n.svg
Path=${dir}
Terminal=true
StartupNotify=false
EOL

chmod 755 "${dir}/start_emulator.sh"
chmod 755 "${home_dir}/Desktop/NB-IoT Emulator.desktop"

