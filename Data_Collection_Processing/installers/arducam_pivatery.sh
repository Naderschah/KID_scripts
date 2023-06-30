cd
wget -O install_pivariety_pkgs.sh https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
chmod +x install_pivariety_pkgs.sh
./install_pivariety_pkgs.sh -p libcamera_dev
# Enable pivatery driver loading
sudo echo "dtoverlay=arducam-pivariety" >> /boot/config.txt
# Enable i2c for camera
sudo echo "dtparam=i2c_arm=on" >> /boot/config.txt
echo "Now reboot"