Here will live all the code related to data collection, file management, and data processing 



ZWO-ASI python https://pypi.org/project/camera-zwo-asi/


## Method of Operation:

### if __name__=='__main__':

Creates logging behavior with file ~/logs/....log

Loads config file with class handler -> extracts each config group as internal variables (paths, pipeline, location) 
FIXME: Pipeline will most likely be removed

Loads file management class --> init creates relevant directories and changes directory to todays imaging routine

double checks camera brand and model against connected to assure correct config file

Retrieves sunset and rise time from some suntime module (FIXME: Check what kind of sunset --> does it really matter?)

Waits for night

Starts imaging and downloading until sunrise time reached

Reexecutes main


### Then from the processing machine:

sftp retrieve directory and run batch pipeline on it after prob using cron depends on preference of computer group

TBD:
- Raspberry image deletion time frame (ie how long do we want a copy on the py)?
- Run everyday as cronjob? cron should have less energy consumption than an idling python script but would need to be recreated everyday to determine start time --> May become a gigantic pain to implement cleanly using python as intermediary


TODO:
- Where are the ZWO SDK docs, I can not find them anywhere -- only option is looking at C source code
- Figure out how whitebalance works in raw files : /main/imgsettings/whitebalance
- Figure out how installation of raspberry can be done prior to inserting the sd card

FIXME:
- Installing apt key is deprecated. Manage Keyring files in trusted.gpg.d instead

## Setting up the raspberry 
This section will be updated frequently

Camera:
Auto-Power-off needs to be manually disabled - gphoto2 seems to not be able to change this setting


- Raspbery installs:
sudo apt update # Basic install requirements - Takes quite some time
sudo apt upgrade 
sudo apt install git # Basic utility requirement

- Gphoto (canon nikon etc):
sudo apt installl gphoto2 # gphoto2 camera control (Canon, Nikon, Samsung etc full list on their site)


- asi drivers CAMERA SHOULD NOT BE CONNECTED
sudo apt install -y wget
wget -O ZWO-SDK.tar.bz2 "https://dl.zwoastro.com/software?app=AsiCameraDriverSdk&platform=macIntel&region=Overseas" # TDOO : Check this link always works
sudo apt install tar
tar -xvjf ZWO-SDK.tar.bz2
# The python package below uses ctypes.util.find_library to find the ASICamera2.h header, it looks through the standard shared libraries so we add the package
sudo cp ASI_linux_mac_SDK_V1.28/include/ASICamera2.h /usr/lib/ASICamera2.h


- python-zwoasi 
git clone https://github.com/python-zwoasi/python-zwoasi.git
cd python-zwoasi
sudo python setup.py install



Raspberry official cam:



Arducam: 



## How do i take a picture why is htis so complicated

pip3 install suntime # Python modules -> will be moved to requirements.txt when completed







Gphoto behavior (temp note):
download/download-all : downloads to current working path 
capture-image-and-download : " and deletes from camera ---> odds are this is the preferred way of doing things