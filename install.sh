#!/bin/bash

reboot=0
project_name=${1:-CamaraFenotipado}

echo "Installing dependencies..."
sudo apt update
sudo apt upgrade -y
sudo apt install -y --no-install-recommends git build-essential libgl1 libglib2.0-0

echo "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -sSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    reboot=1
    echo " | Installed and configured user"
else
    echo " | Docker already installed"
fi

echo "Configuring I2C and Serial hardware..."
if [ "$(sudo raspi-config nonint get_i2c)" -ne 0 ]; then
    sudo raspi-config nonint do_i2c 0
    reboot=1
    echo " | Enabled I2C"
fi
if grep -q "console=serial0" /boot/firmware/cmdline.txt; then
    sudo sed -i 's/console=serial0,[^ ]* //g' /boot/firmware/cmdline.txt
    reboot=1
    echo " | Disabled Serial console"
fi
if ! grep -qxF "enable_uart=1" /boot/firmware/config.txt; then
    echo "enable_uart=1" | sudo tee -a /boot/firmware/config.txt
    reboot=1
    echo " | Enabled UART hardware"
fi
if ! grep -qxF "dtoverlay=disable-bt" /boot/firmware/config.txt; then
    echo "dtoverlay=disable-bt" | sudo tee -a /boot/firmware/config.txt
    reboot=1
    echo " | Disabled Bluetooth"
fi

echo "Cloning repo..."
git clone https://github.com/LuisFelipe2204/camara-fenotipado $project_name
cd $project_name

echo "Setting up virtual environment..."
cp .env.example .env

cd wifi
python3 -m venv env-wifi
source env-wifi/bin/activate
pip install --upgrade pip setuptools
pip install --no-cache-dir -r requirements.txt

printf "Set up complete. "
if [ "$reboot" -eq 1 ]; then
    echo "Rebooting..."
    sudo reboot
else
    echo "No reboot required."
fi