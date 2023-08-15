sudo apt install python3-numpy python3-numpy python3-pip git vim tmux 
pip3 install suntime PILLOW

sudo apt-get install -y libltdl-dev libusb-dev libusb-1.0 libexif-dev libpopt-dev

# Download correct version for libgphoto2 

wget http://downloads.sourceforge.net/project/gphoto/libgphoto/2.5.30/libgphoto2-2.5.30.tar.gz

# Get correct gphoto2

wget https://sourceforge.net/projects/gphoto/files/gphoto/2.5.28/gphoto2-2.5.28.tar.gz


# Unpack and install libgphoto2

tar -xvzf libgphoto2-2.5.30.tar.gz
cd libgphoto2-2.5.30
./configure
make
sudo make install

cd ~

# Gphoto2

tar -xvzf gphoto2-2.5.28.tar.gz
cd gphoto2-2.5.28
./configure
make
sudo make install

# Make sym link

cd ~
sudo ln -s $(pwd)/gphoto2-2.5.28/gphoto2/gphoto2 /usr/bin/gphoto2

# Test

gphoto2 --version

