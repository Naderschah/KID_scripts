# Code to make the makeshift spectroscope work


Camera algorithms 
https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf

Most code will be taken from : https://github.com/leswright1977/PySpectrometer2/

In the stl folder one can find files to 3dprint to assemble this using the following component

Focusing of the lens should be done with a montior connected using the QT preview, over ssh its way to slow to be usefull 

TODO: Check how to combine curve fit continously with focus

TODO:

The intent is to create a non-graphical version capable of working at night

Calibration is easiest done using the graphical software from PySpectrometer, keybindings are on the git page

Tuning file at: /usr/share/libcamera/ipa/raspberrypi


Solar reference spectrum taken from:
https://www.sciencedirect.com/science/article/abs/pii/S0022407310000610

Baader spectrum image converted to csv data using : apps.automeris.io/wpd


Modified tuning file and disabled all correction algorithms