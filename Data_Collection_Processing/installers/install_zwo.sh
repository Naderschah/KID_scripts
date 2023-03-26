#!/bin/bash
apt update 
apt upgrade -y
apt install -y git wget tar python3-setuptools python3-numpy swig python3-dev

# Get SDK
wget -O ZWO-SDK.tar.bz2 "https://dl.zwoastro.com/software?app=AsiCameraDriverSdk&platform=macIntel&region=Overseas"
tar -xvjf ZWO-SDK.tar.bz2
# Figure out architecture
val=$(more /proc/cpuinfo | grep model);b=${val:13:5};b=${b,,};echo "Architecture $b" 
# Add python header files to shared package dir -- there has to be an easier way to move all the files
cp ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* /usr/local/lib 
cp ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* /usr/lib 
cp ASI_linux_mac_SDK_V1.28/lib/zwo/1.18/linux_sdk/include/ASICamera2.h /usr/local/lib 
cp ASI_linux_mac_SDK_V1.28/lib/zwo/1.18/linux_sdk/include/ASICamera2.h /usr/lib 
cd ASI_linux_mac_SDK_*/lib
sudo install asi.rules /lib/udev/rules.d 

# Install python package and requirements : Check if above still required
sudo bash -c 'echo "deb [trusted=yes] https://apt.fury.io/jgottula/ /" > /etc/apt/sources.list.d/jgottula.list's
sudo apt update
sudo apt install -y libasicamera2 python3-dev

git clone https://github.com/seeing-things/zwo.git
cd zwo/python
# Why the hell is this required --- there must be docs for this somewhere
cp ~/ASI_linux_mac_SDK_V1.28/lib/zwo/1.18/linux_sdk/include/ASICamera2.h  .
cp ~/ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* .
cp ~/ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* build/lib.linux-armv6l-3.9/
cp ~/ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* dist/
python3 setup.py install 



# The _asi package is in build/lib.linux-armv6l-3.9/ , the asi package is hosted in the zwo folder, the header and so files are required everywhere for some goddamn reason and i dont want to figure out which lcoations are required, as 1 was required for install and 1 for deployment, i dont recall which was correct  
