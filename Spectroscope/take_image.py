#!/usr/bin/python3
### Sample script to take an image with controlled parameters

import time
from picamera2 import Picamera2, Preview, Controls
from libcamera import controls
import sys
from PIL import Image
import numpy as np
import os


tuning = Picamera2.load_tuning_file(os.path.abspath("./tuningfile_ov5647.json"))
picam2 = Picamera2(tuning=tuning)
num_im = 1
dark = False
filename = None
hdr = False
# Set values as required
ctrl = {    "ExposureTime":100000 + 22,  # It subtracts 22 for some reason from each exposure
            "AnalogueGain":1, 
            "AeEnable": False,  # Auto Exposure Value
            "AwbEnable":False,  # Auto White Balance
            "Brightness":0, # Default
            # 3x3 matrix to be used by ISP to convert raw colors to sRGB --> -16 to 16 :: Use 0 so that all is handled by spectroscope
            # This is never actually passed but determined from color gains --> seems its only for bayer->rgb so not important for raw
            "ColourCorrectionMatrix": (0.,0.,0.,0.,0.,0,0.,0.,0.),
            # TODO: Maybe revisit below to improve STN (should be wavelength dependent no?)
            "ColourGains":(1.,1.), # Red and blue gains -> 0,0 so that Analogeu Gain is the only parameter
            "ExposureValue":0, # No exposure Val compensation --> Shouldnt be required as AeEnable:False
            "NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off, # No Noise reduction --> No idea how it works
} # Note: Digital Gain is automatically set!

# Bias approx 5 s per image
if '-b' in sys.argv: # In the source code exposure_time = int(1/(self.metadata["ExposureTime"] * 0.000001))  /usr/lib/python3/dist-packages/pidng/camdefs.py", line 100, in __settings__ TODO: figure out why 
    ctrl["ExposureTime"] = picam2.sensor_modes[-1]['exposure_limits'][0] 
    num_im = 100

# Dark
if '-d' in sys.argv:
    num_im = 100
    dark = True

if '-n' in sys.argv:
    num_im = int(sys.argv[int(sys.argv.index('-n'))+1])

if '-f' in sys.argv:
    filename = sys.argv[int(sys.argv.index('-f'))+1]

if '-e' in sys.argv:
    exp = int(sys.argv[int(sys.argv.index('-e'))+1])
    ctrl["ExposureTime"] = exp + 22 # It subtracts 22 for some reason from each exposure
    if exp < picam2.sensor_modes[-1]['exposure_limits'][0]:
        print('Less than minimum exposure time: Setting {}'.format(picam2.sensor_modes[-1]['exposure_limits'][0]))
        ctrl["ExposureTime"] = picam2.sensor_modes[-1]['exposure_limits'][0]
    # TODO : Comment may be wrong
    print('Set exposure to: ', ctrl["ExposureTime"])

if '-hdr' in sys.argv:
    hdr = True


if '-h' in sys.argv and not '-hdr' in sys.argv:
    print('Takes images with everything turned off and ISO at minimum value\nColor Correction Matrix still needs to be Fixed!\n -b Take bias images (n=100) \n -d take dark images (n=100) \n -n overwrite number of images \n -f filename for output dont add an extension! \n -e change exposure (10^-6s)')
    sys.exit(0)



print('Initiating with filename:{}, num_im: {}'.format(filename,num_im))

# Sensor modes for the Waveshare 5MP
 #[{'format': SGBRG10_CSI2P, 'unpacked': 'SGBRG10', 'bit_depth': 10, 'size': (640, 480), 'fps': 58.92, 'crop_limits': (16, 0, 2560, 1920), 'exposure_limits': (134, 1103219, None)},
 # {'format': SGBRG10_CSI2P, 'unpacked': 'SGBRG10', 'bit_depth': 10, 'size': (1296, 972), 'fps': 43.25, 'crop_limits': (0, 0, 2592, 1944), 'exposure_limits': (92, 760636, None)}, 
 # {'format': SGBRG10_CSI2P, 'unpacked': 'SGBRG10', 'bit_depth': 10, 'size': (1920, 1080), 'fps': 30.62, 'crop_limits': (348, 434, 1928, 1080), 'exposure_limits': (118, 969249, None)}, 
 # {'format': SGBRG10_CSI2P, 'unpacked': 'SGBRG10', 'bit_depth': 10, 'size': (2592, 1944), 'fps': 15.63, 'crop_limits': (0, 0, 2592, 1944), 'exposure_limits': (130, 1064891, None)}]
# For this sensor all sensor modes appear to have the same relative sensitivity to double check you will want to iterate over the following to get the highest relative sensor Sensitivity parameter
# picam2.configure(picam2.create_preview_configuration(raw=picam2.sensor_modes[0]))
# picam2.camera_properties

# Capture a DNG.

capture_config = picam2.create_still_configuration(raw={})
picam2.configure(capture_config)
picam2.set_controls(ctrl)
exp_lim = picam2.sensor_modes[-1]['exposure_limits']


picam2.start()

time.sleep(2)

meta = {}
if not hdr:
    for i in range(0,num_im):
        request = picam2.capture_request()
        if filename is None and num_im>1:
            request.save_dng("img_{}.dng".format(i))
            meta["{}_{}".format('img',i)] = request.get_metadata()
        elif filename is None and num_im==1:
            request.save_dng("img.dng")
            request.save("main","img.jpg")
            filename = "img"
            meta = request.get_metadata()
        elif filename is not None and num_im==1:
            request.save_dng("{}.dng".format(filename))
            request.save("main","{}.jpg".format(filename))
            meta = request.get_metadata()
        elif filename is not None and num_im>1:
            request.save_dng("{}_{}.dng".format(filename,i))
            meta["{}_{}".format(filename,i)] = request.get_metadata()
        request.release()  # requests must always be returned to libcamera
        print('took image ',i)
        
if hdr: 
    for i in np.linspace(exp_lim[0],exp_lim[1],20):
        # Make int
        i = int(i)
        # Set exp
        ctrl['ExposureTime'] = i
        print('Set exp: ',i)
        picam2.set_controls(ctrl)
        time.sleep(2)
        # Take num_im images 
        for j in range(0,num_im):
            request = picam2.capture_request()
            if filename is not None:
                f="{}_{}_{}.dng".format(filename,i,j)
                request.save_dng(f)
            else:
                f = "img_{}_{}.dng".format(i,j)
                request.save_dng(f)
            if j == num_im-1:
                request.save("main","img.jpg")
            request.release()  # requests must always be returned to libcamera
        im = np.asarray(Image.open('img.jpg'))
        # Break for loop when a third  of image overexposed
        if np.sum((im==255))/im.size > 0.3:
            break



picam2.stop()
