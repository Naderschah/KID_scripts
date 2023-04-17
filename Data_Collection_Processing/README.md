Here will live all the code related to data collection, file management, and data processing 



ZWO-ASI python https://pypi.org/project/camera-zwo-asi/


## Method of Operation:

config.ini file needs to be filled, for more options more code is required (as the internal names arent the same as the ones we know)

Code is to be run in tmux (persistent terminal that doesnt close when the ssh session does)

If there was no previous tmux session

tmux new -s imaging

To reattach: 

tmux a -t imaging

To detach ctrl+b d (so press ctrl and b then let go and hit d seperately)

Cheat Sheet: https://tmuxcheatsheet.com/

If you cant scroll in tmux use keyboard or add to ~/.tmux.conf : set -g mouse on

### Config File
to run add all the parameters to the config file:

Under [Camera]:

Brand : The name of the brand, on error you need to check what it actually is (gphoto --list-devices)

Model : Model Name, on error same as above

Exposure : Time in seconds, or camera recognized key --> if not recognized TODO: Switch to bulb and set manually

ISO : ISO in whatever unit the camera accepts: FIXME : Whats it in the ZWO there dont seem to be bounds so im assuming digital is used

Image_Frequency : time between images in minutes

Image_Format : Only relevant for Canon etc. RAW should be the goto

Under [Paths]:

FIXME:

Under 

### if __name__=='__main__':

Creates logging behavior with file ~/logs/....log

Loads config file with class handler -> extracts each config group as internal variables (paths, location) 

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
- Figure out how whitebalance works in raw files : /main/imgsettings/whitebalance  - is it an important imaging parameter or corrected for after the fact
- Figure out how installation of raspberry can be done prior to inserting the sd card -- ie make iso files that can be used with rpi-imager (for username and passwords etc)

FIXME:
- Installing apt key is deprecated. Manage Keyring files in trusted.gpg.d instead -- Figure out what this was about

## Setting up the raspberry 

Use the installer script relevant to the camera in use located in the installers folder

TODO: Double check each on clean install, write the one for gphoto





Gphoto behavior (temp note):
download/download-all : downloads to current working path 
capture-image-and-download : " and deletes from camera ---> odds are this is the preferred way of doing things