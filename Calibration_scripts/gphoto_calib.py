import subprocess
import sys
import rawpy
import numpy as np

if '-h' in sys.argv:
    print('CMD line tool to take images with gphoto supported camera\nOnly specify one flag at a time (-n can always be put except for linearity, -f can always be put)\n -b : Take Bias images\n -d : Take dark images\n -f Output filenames \n -l Take linearity images \n -n nr. : Overwrite the number of images with nr.\n -h this')
    sys.exit(0)

#            Check some camera is connected recognized by gphoto
result = subprocess.run(["gphoto2 --auto-detect"], capture_output=True,check=True,shell=True)
# shutter speed setting : /main/capturesettings/shutterspeed
# ISO setting : /main/imgsettings/iso
print('Make sure that all settings that may interfere are turned off')


# Get Exposure and ISO values and turn to list
result = subprocess.run(["gphoto2 --get-config /main/capturesettings/shutterspeed"], capture_output=True,check=True,shell=True)
result = result.stdout.split('\n')
# Create dict {choice nr: ISO val, ...}
exposure = {int(i.split(' ')[1]):float(i.split(' ')[2]) for i in result if 'choice' in i.lower() and not 'auto' in i.lower()}

# Get Exposure
result = subprocess.run(["gphoto2 --get-config /main/imgsettings/iso"], capture_output=True,check=True,shell=True)
result = result.stdout.split('\n')
# Create dict {choice nr: shutter val, ...}
iso = {int(i.split(' ')[1]):int(i.split(' ')[2]) for i in result if 'choice' in i.lower() and not 'auto' in i.lower()}


#               Cmd line parsing
Bias = False
Dark = False
Flat = False
Linearity = False
num_im = 10
filename = None

if '-b' in sys.argv: # In the source code exposure_time = int(1/(self.metadata["ExposureTime"] * 0.000001))  /usr/lib/python3/dist-packages/pidng/camdefs.py", line 100, in __settings__ TODO: figure out why 
    Bias = True
    num_im = 20

# Dark
if '-d' in sys.argv:
    num_im = 100
    Dark = True

if '-f' in sys.argv:
    raise NotImplementedError('Prob not going to ')
    filename = sys.argv[int(sys.argv.index('-f'))+1]

if '-l' in sys.argv:
    Linearity = True
    
if '-f' in sys.argv:
    Flat = True

if '-n' in sys.argv:
    num_im = int(sys.argv[int(sys.argv.index('-n'))+1])


def set_config_entry(self,entry, value):
    """Applies individual config"""
    result = subprocess.run(["gphoto2 --set-config {}={}".format(entry, value)], capture_output=True,check=True,shell=True)
    if result.returncode != 0:
        raise Exception('Setting config value failed with the command output printed above')
    
if Linearity:
    # Go from short to long exposure
    exp = [key for key in exposure].reverse()
    # Go from small to large iso 
    iso = [key for key in iso]
    # Now iterate over both lists and terminate each level when signal to large
    for i in exp:
        set_config_entry('/main/capturesettings/shutterspeed', i)
        for j in iso:
            set_config_entry('/main/imgsettings/iso', j)
            result = subprocess.run(['gphoto2 --capture-image-and-download --filename "%Y%m%d%H%M%S.cr2"'], capture_output=True,check=True,shell=True)
            fname = result.stdout.split('\n')[1].split(' ')[-1]
            # Load and check if half the pixels are overexposed TODO: Find quicker method
            img = rawpy.imread(fname)
            max_val = np.iinfo(img.raw_image.dtype).max
            bool_arr = img.raw_image == max_val
            if np.sum(bool_arr) / bool_arr.shape > 0.5:
                print('Overexposed at Exp: {}, ISO: {}'.format(i,j))
                break


elif Bias:
    set_config_entry('/main/capturesettings/shutterspeed', [key for key in exposure][-1])
    for key in iso:
        set_config_entry('/main/imgsettings/iso', key)
        for i in num_im:
            result = subprocess.run(['gphoto2 --capture-image-and-download --filename "%Y%m%d%H%M%S.cr2"'], capture_output=True,check=True,shell=True)
