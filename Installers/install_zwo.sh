#!/bin/bash

echo "Changing Working Directory to home"

cd ~

sudo apt update 
sudo apt upgrade -y
sudo apt install -y git wget tar exiftool vim python3-setuptools python3-numpy swig python3-dev python3-suntime tmux # Basic utility requirement (tmux for persistent session over ssh)

# Get SDK
wget -O ZWO-SDK.tar.bz2 "https://dl.zwoastro.com/software?app=AsiCameraDriverSdk&platform=macIntel&region=Overseas"
# Check this works, for some reason sometimes they give a tar.bz2 file and sometimes a  zip file 
if tar -xvjf ZWO-SDK.tar.bz2 ; then
echo "Untarring successful"
else
    echo "Untarring unsuccessfull\nAttempting unzipping" 
    sudo apt install -y unzip
    mv ZWO-SDK.tar.bz2 ZWO-SDK.zip
    if  unzip ZWO-SDK.zip ; then 
    echo "Unzip Successful"
    else
    echo "Extracting ZWO files failed download from https://dl.zwoastro.com/software?app=AsiCameraDriverSdk&platform=macIntel&region=Overseas and fix script extension" 
    fi
fi
# Figure out architecture
val=$(more /proc/cpuinfo | grep model);b=${val:13:5};b=${b,,};echo "Architecture $b" 
# Add python header files to shared package dir -- there has to be an easier way to move all the files
sudo cp ~/ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* /usr/local/lib 
sudo cp ~/ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* /usr/lib 
sudo cp ~/ASI_linux_mac_SDK_V1.28/include/ASICamera2.h /usr/local/lib 
sudo cp ~/ASI_linux_mac_SDK_V1.28/include/ASICamera2.h /usr/lib 
sudo cd ASI_linux_mac_SDK_*/lib
sudo install asi.rules /lib/udev/rules.d 

# Install python package and requirements : Check if above still required
sudo bash -c 'echo "deb [trusted=yes] https://apt.fury.io/jgottula/ /" > /etc/apt/sources.list.d/jgottula.list's
sudo apt update
sudo apt install -y libasicamera2 python3-dev

git clone https://github.com/seeing-things/zwo.git
cd zwo/python
# THis will fail but create directories to copy header files into so we can make it run again
sudo python3 setup.py install 

# Doesnt look in the right dir just copy it
sudo cp ~/ASI_linux_mac_SDK_V1.28/include/ASICamera2.h  ~/zwo/python/
sudo cp ~/ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* ~/zwo/python/


sudo cp ~/ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* ~/zwo/python/build/lib.linux-armv6l-3.9/
sudo cp ~/ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.* ~/zwo/python/dist/

sudo python3 setup.py install 


# The _asi package is in build/lib.linux-armv6l-3.9/ , the asi package is hosted in the zwo folder, the header and so files are required everywhere for some goddamn reason and i dont want to figure out which lcoations are required, as 1 was required for install and 1 for deployment, i dont recall which was correct  
