# KID_scripts

Random scripts associated with the keep it dark project




Using Seperate dockerized conda enviorment for general coding in this project, found in directory root




### cloud_mapping
some scripts and utility how long it would have taken in the past to map a given surface area using sentinel orbits and covarage

Proxy for high res images feasibilty of location

Sadly high resolution images without clouds are sparse using only one cluster

Only way to do complete Wadden area mapping (might as well do the entire world while at it) is to source data from several companies satellite clusters of differing resolutions and sensitivities


### AllSkyImageProcessing

A batch processing script (written in python2) for pyASB, note the script doesnt fully work yet and we dont know if PyASB fully works yet

TODO:

### Data_Collection_Processing

Framework for taking periodic images transfering to a raspberry, includes a config file for configuration, a file handler (really basic saves in root as day encoded directory and datetime encoded file names for each image).

The intent is that the collected data will daily be retrived by the kapteyn servers through sftp and processed there

All of this is really basic, however, none of it was tested for edge cases yet (I/O error, camera unresponsive, etc)



### Spectrometer

Adapted code to run a makeshift spectrometer, more info in its documentation


### Random Notes:

Lens distortion database: https://github.com/letmaik/lensfunpy