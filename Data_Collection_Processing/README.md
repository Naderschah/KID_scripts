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


- asi drivers CAMERA SHOULD NOT BE CONNECTED : http://instrumentation.obs.carnegiescience.edu/Software/ZWO/Setup/setup.html
sudo apt install -y wget python3-setuptools python3-numpy swig
wget -O ZWO-SDK.tar.bz2 "https://dl.zwoastro.com/software?app=AsiCameraDriverSdk&platform=macIntel&region=Overseas" # TDOO : Check this link always works
sudo apt install tar
tar -xvjf ZWO-SDK.tar.bz2
# Figure out architecture
val=$(more /proc/cpuinfo | grep model);b=${val:13:5};b=${b,,};echo "Architecture $b" 
# Add python header file to shared package dir
sudo cp ASI_linux_mac_SDK_V1.28/lib/$b/libASICamera2.so.1.27 /usr/local/lib 
cd ASI_linux_mac_SDK_*/lib
sudo install asi.rules /lib/udev/rules.d 

Trialed Packages
- seeing-things/zwo - Uses swig
The download procedure is in the install script, quite a few of the steps are not required, however, its not worth figuring out which those are as the installation is already incredibly hacky 


Raspberry official cam:



Arducam: 



## How do i take a picture why is htis so complicated

pip3 install suntime # Python modules -> will be moved to requirements.txt when completed







Gphoto behavior (temp note):
download/download-all : downloads to current working path 
capture-image-and-download : " and deletes from camera ---> odds are this is the preferred way of doing things