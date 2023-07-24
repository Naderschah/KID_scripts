## Config Files

All types of config files (standard python config ini files) my imaging scripts accept. 

I will cover individual groups in the config rather than individual configs.

[Camera]

- Brand : Accepts ZWO, Canon, Nikon, PiCamera, Waveshare, Arducam

Here the only unique choices are the groups of (ZWO), (Canon, Nikon), (PiCamera, Waveshare, Arducam)

Where the first tells the script to use the ZWO C backend (see installers or class overview)

The second calls the gphoto backend (the cmd line version not the python package, noticed too late the python package exists), where this is a backengineered PTP protocoll, so issues will likely arrise, be aware with newer cameras

And the last calls the PiCamera2 python backend, which is based on libcamera and in turns based on v4l2 (i think, not sure about the last one ) 


- Model : Needs to be the model of the camera, raises an error if the model in the config file and the model of the respective backends dont align, makes no difference to the (PiCamera, Waveshare, Arducam) backend. For ZWO this gets excplicitly added to the exifdata (among other things), but is checked first, if your not sure run the script it will tell you what model is connected

- Exposure : Exposure time in seconds or Auto, Auto does not work for all backends, it works for ZWO (not tested in the field only at home as of 2022-07-22), and for PiCamera it uses a shitty convergence script that I will hopefully fix before I leave, in PiCamera this also adjusts ISO if increasing Exposure does not yield satisfying results

- ISO : Taken to be constant so 100 200 whatever the camera accepts, for PiCamera I think it is in mV and the ISO value reported in exif is 100 times that, however note that this is not ISO but AnalogueGain, where the ISO conversion is Wrong! (Then again ISO is poorly defined from my understanding), if a too large value is passed, DigitalGain should automatically be applied allthough I generally go for the lowest possible value

- Image_Frequency : sleep time after image in minutes (in code gets taken as int(Image_Frequency * 60) or for picamera int(Image_Frequency * 60)*1e6 choose your precision from that)

- Image_Format : Pointless variable I added originally, too much work to remove so always specify as RAW


### This Completes the mandatory points now to the application specific ones

- Application : So far only accepts Spectroscope, tells it to apply spectrometer specific processing TODO: Did i add this already?

- Tuning_File : Absolute Path to tuning file for Picamera tuning, this allows to minimize the effect the ISP has on the images, in the code I tried to use this to fix ISP based auto exposure but to no success I could never get it to auto expose for some reason, the package is a bit finicky so I avoid doing it

- Spectro_Metering : (bool: True/False)  For ISP auto exposure (does not work - and also selects the wrong fields never included the start top parameters here), and custom exposure for custom exposure these 4 points can be given as seperate entries X_start, Y_start, X_end, Y_end in case the spectrum does not cover the entire image

- HDR : (bool: True/False) If true Takes images at 0.5,0.8,0.9,1.1,1.2,1.5 times the exposure time (may be overkill will see) to increase the dynamic range of the image



[Paths]

- FILE_SAVE : Directory where files are saved
- REMOTE_SAVE = None  : Not required originally wanted to handle this py based but safer (and easier) to do server side


[Pipeline]

- executable = None : Data processing pipeline, never used



[Location]
- longitude : As the name suggests, for meta data and computing sunset/rise
- latitude   : As the name suggests, for meta data and computing sunset/rise



[MotorAzi]

Handles Motor control pins for horizon cameras, MotorAlt also possible but no designs made and code for it missing, should be easy enough to add

- msx : gpio pin number for ms controller pin x (for board used 1 to 4, for different board you will need to add an entry here specifying what driver to use and write a seperate backend)

- step_size : step between images to take in degrees - the conv constant in the backend needs to be correct for this to work properly (but if its off can be fixed with astrometry is already set up)

