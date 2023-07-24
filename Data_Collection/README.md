
# Data Collection 

Houses all scripts related to data collection. 

Contains ZWO, Canon(and anything else gphoto2 supports), and PiCamera backends, with specific tools for Spectroscopy (PiCamera based), and horizon cameras using the ULN_2003 driver board, 28BYJ-48 stepper motor, but for others a backend canb be added, but does require modification of config file and main code to allow for this behavior

Directories within this directory: 

- conf_files : Configuration files used by main script for several camera set ups, README within

- cron_scripts : Cron scripts used to make the camera scripts autolaunch etc, README within