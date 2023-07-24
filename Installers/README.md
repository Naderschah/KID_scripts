## Installers

All installers for everything I was working on will be contained within this directory, the scripts found here are:
- arducam_pivatery.sh : Installs the drivers for arducams pivatery camera
- install_gphoto.sh : FIXME
- install_zwo.sh : Installs zwo c backend library and the python package I chose to interface with this
- install_picamera.sh : Installs the picamera set up FIXME

The individual installers are not required and are just steps I noted down so that I could remember how I did things

The full installers are found in: TODO
- install_gphoto_camera.sh : Used to set up raspberries for imaging with Canon EOS 6D Mark II and EOS RP : For different cameras check that the version of libcamera(=5.30) that gets installed supports your camera
- install_moving_camera.sh : Used for the horizon cameras set up with the ULN_2003 driver board, 28BYJ-48 stepper motor and any standard raspberry camera, for pivatery from arducam the install_arducam.sh script also needs to be run
- install_zwo_camera.sh : Used to install everything to get the ZWO cameras running : Untested! FIXME

