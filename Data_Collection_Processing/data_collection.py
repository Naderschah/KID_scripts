import configparser as cfg
import subprocess
import os
import datetime
import suntime
import copy
import time
import logging
import re
import time
import numpy as np
from PIL import Image
import tarfile
import subprocess

try:
    import asi
except:
    pass

try:
    from picamera2 import Picamera2, Preview, Controls
    from libcamera import controls
except:
    pass

"""Class that handles camera control, i.e. image taking 
Below is a list of backends and camera combinations that are to be used 
    gphoto2 (http://www.gphoto.org/proj/libgphoto2/support.php):
Canon 6D
Canon RP
    Note that for this backend I will not be using the python ported library but simply will execute the CMD line from within python

The config file is expected to be called config.ini in the same directory as this file
As long as config is in it and it ends in ini it is recognized
"""

DEBUG = True



### IMPORTANT: I do not get how loggers work, I have had only inconsistent reults this may need reworking
CODE_DIR = os.path.abspath(os.getcwd())

logFormatter = logging.Formatter("%(asctime)s [line: %(lineno)d] [%(levelname)-5.5s]  \n%(message)s")
ROOTLOGGER = logging.getLogger()
# Set lowest possible level so it catches all
ROOTLOGGER.setLevel(logging.DEBUG)

if not os.path.isdir(os.path.join(CODE_DIR, 'logs')):
    os.mkdir(os.path.join(CODE_DIR, 'logs'))

fileHandler = logging.FileHandler(os.path.join(CODE_DIR, 'logs', '{}.log'.format(datetime.datetime.now().strftime("%Y%m%d"))))
print(os.path.join(CODE_DIR, 'logs' 'logs.log'))
fileHandler.setFormatter(logFormatter)
ROOTLOGGER.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
ROOTLOGGER.addHandler(consoleHandler)

ROOTLOGGER.info('Created ROOTLOGGER')



def main():
    # Retrieve config file
    config_path = os.path.join(CODE_DIR,'config.ini')

    # Check for some config file
    if os.path.isfile(config_path):
        pass
    else:
        fl = os.listdir(CODE_DIR)
        bool_fl = ['config' in i and i.endswith('.ini') for i in fl]
        if sum(bool_fl)>1 or sum(bool_fl)==0:
            print('Fix the config file\nIt needs to be in the same directory as the script and have config in its name and end in .ini')
        filen = [fl[i] for i in range(len(fl)) if bool_fl[i]][0]
        config_path = os.path.join(CODE_DIR,filen)
    
    config = Config_Handler(path=os.path.join(CODE_DIR,'config.ini'))

    # Sets up folder for night and switches directory
    file_handler = File_Handler(config.paths)
    # Set up camera control - each init will check the correct camera and brand is 
    if config.camera['Brand'] in ["Canon", "Nikon"]: # Add the other ones if required
        ROOTLOGGER.info("Using gphoto2 as backend")
        camera = Camera_Handler_gphoto(config)
    elif config.camera['Brand'] == "ZWO": 
        ROOTLOGGER.info("Using zwo asi sdk backend (not sure what asi stands for)")
        camera = Camera_Hanlder_ZWO(config)
    elif config.camera['Brand'] == "PiCamera": 
        ROOTLOGGER.info("Using picamera backend")
        camera = Camera_Handler_picamera(config)

    # Check time to start
    if not DEBUG:
        sun = suntime.Sun(float(config.location['longitude']), float(config.location['latitude']))
        start = sun.get_sunset_time()
        end = sun.get_sunrise_time(datetime.datetime.now()+datetime.timedelta(days=1))
    else:
        start = datetime.datetime.now(datetime.timezone.utc)
        end = start+datetime.timedelta(days=1)

    ROOTLOGGER.info('Imaging start time: {} \nImaging stop time: {}'.format(start,end))

    while datetime.datetime.now(datetime.timezone.utc)<start:
        ROOTLOGGER.info("Waiting for night")
        print("Waiting for night")
        time.sleep((start-datetime.datetime.now(datetime.timezone.utc)).total_seconds())
    ROOTLOGGER.info('Starting Imaging')
    counter = 1
    while datetime.datetime.now(datetime.timezone.utc)<end:
        print('Taking image ', counter)
        camera.capture_image_and_download()
        time.sleep(int(config.camera['Image_Frequency'])*60)
        counter += 1
    ROOTLOGGER.info('Total number of images ', counter)
    # The below is for cameras that require closing at the end of the night
    camera.finish()
    # Now we also compress the created data
    with tarfile.open(file_handler.img_path.split('/')[-1]+'.tar.gz', "w:gz") as tar:
        tar.add(file_handler.img_path, arcname=os.path.basename(file_handler.img_path))
    os.remove(file_handler.img_path)
    main()

    

class Camera_Hanlder_ZWO: # FIXME: Autmatic Dark Subtraction - trial what it does?
    """Camera handler for ZWO devices
    """
     # No docs, mess around in python interactive to find commands 
    # Controls need to be individually indexed and will be added to the below dictionary
    controls = {} # Name : swig_object
    error_codes = {0:'ASI_SUCCESS', 1:'ASI_ERROR_INVALID_INDEX',2:'ASI_ERROR_INVALID_ID',
                   3:'ASI_ERROR_INVALID_CONTROL_TYPE', 4:'ASI_ERROR_CAMERA_CLOSED',
                   5:'ASI_ERROR_CAMERA_REMOVED', 6:'ASI_ERROR_INVALID_PATH', 7:'ASI_ERROR_INVALID_FILEFORMAT',
                   8:'ASI_ERROR_INVALID_SIZE', 9:'ASI_ERROR_INVALID_IMGTYPE',10:'ASI_ERROR_OUTOF_BOUNDARY',
                   11:'ASI_ERROR_TIMEOUT',12:'ASI_ERROR_INVALID_SEQUENCE',13:'ASI_ERROR_BUFFER_TOO_SMALL',
                   14:'ASI_ERROR_VIDEO_MODE_ACTIVE',15:'ASI_ERROR_EXPOSURE_IN_PROGRESS',16:'ASI_ERROR_GENERAL_ERROR',
                   17:'ASI_ERROR_END'}
    # TODO: Add error codes to failures
    auto_exp = False

    def __init__(self,config_handler) -> None:
        self.config = config_handler.camera
        if asi.ASIGetNumOfConnectedCameras() == 0:
            logging.error("No camera detected")
            raise Exception("No camera detected check drivers")
        else:
            logging.info("ZWO camera detected")
        rtn, self.info = asi.ASIGetCameraProperty(0)
        if rtn != asi.ASI_SUCCESS:  # ASI_SUCCESS == 0
            # FIXME: On restart camera needs to be reconnected - find a way to do that digitally
            logging.error("Driver not working as expected, failure expected")
        if self.config['Brand']+' '+self.config['Model'] != self.info.Name:
            logging.warning("Camera Brand mismatch! Expected {} Found {}".format(self.config['Brand']+' '+self.config['Model'] , self.info.Name))
        self.set_up_camera()
        self.get_controls()
        self.set_controls()
        
    def set_up_camera(self):
        """Does basic setup"""
        out = asi.ASIOpenCamera(self.info.CameraID)
        if out != asi.ASI_SUCCESS: logging.warning("Open Camera Failed! {}".format(out))
        out = asi.ASIInitCamera(self.info.CameraID)
        if out != asi.ASI_SUCCESS: logging.warning("Init Camera Failed! {}".format(out))
        # Set video mode default is mono ( I think )
        out = asi.ASISetROIFormat(
                self.info.CameraID, 
                self.info.MaxWidth, # Img dim
                self.info.MaxHeight, # Img dim
                1, # Binning 
                asi.ASI_IMG_RGB24 # IMG type
            )
        if out != asi.ASI_SUCCESS: logging.error("Could not set ROI format. Error code: {}".format(out))

        return None

    def get_controls(self):
        """We need to create the controls dictionary ourselves"""
        rtn, num_controls = asi.ASIGetNumOfControls(self.info.CameraID)
        for control_index in range(num_controls):
            rtn, caps = asi.ASIGetControlCaps(self.info.CameraID, control_index)
            self.controls[caps.Name] = caps

        return None

    def set_controls(self):
        """
        Sets controls based on mapping dict from config names to control type name 
        Name output : index
        Gain 0
        Exposure 1
        WB_R 3
        WB_B 4
        Offset 5
        BandWidth 6
        Flip 9
        AutoExpMaxGain 10
        AutoExpMaxExpMS 11
        AutoExpTargetBrightness 12
        HardwareBin  13
        HighSpeedMode 14
        MonoBin 18
        Temperature 8 (not writable)
        GPS 22 (not writable - 0 )
        """
        config_subset = {}
        # add relevant indexes and do typing
        config_subset[0] = int(self.config['ISO'])
        auto_exp=False
        if 'Auto'==self.config['Exposure']:
            self.config.pop('Exposure')
            auto_exp = True

        elif "/" in self.config['Exposure']:
            n, d = self.config['Exposure'].split('/')
            # convert to micro s
            config_subset[1] = int(float(n)/float(d)*1e6)
        else:
            config_subset[1] = float(self.config['Exposure'])*1e6

        for key in config_subset:
            # Params (cam id, control caps reference, value to bne set, bool autoadjust value)
            # It wants cam id as a swift object, control caps as the int identifier,
            asi.ASISetControlValue(self.info.CameraID,key, int(config_subset[key]), asi.ASI_FALSE)
        
        if auto_exp:
            # Sets AutoExpTargetBrightness to 100
            asi.ASISetControlValue(self.info.CameraID, 12, 100, asi.ASI_TRUE)
            # Set autoadjust exposure -> Value doesnt matter will be autoadjusted later
            asi.ASISetControlValue(self.info.CameraID, 1, 100, asi.ASI_TRUE)
            # Run twice, doesnt always take if run once
            asi.ASISetControlValue(self.info.CameraID, 1, 100, asi.ASI_TRUE)
            # Before each image the camera will need to autocompute these settings, the computation is moved before imagee capture
            self.auto_exp = True

        # Print to log file
        logging.info("Final Configuration:")
        rtn, num_controls = asi.ASIGetNumOfControls(self.info.CameraID)
        for control_index in range(num_controls):
            rtn, caps = asi.ASIGetControlCaps(self.info.CameraID, control_index)
            rtn, value, _ = asi.ASIGetControlValue(self.info.CameraID, caps.ControlType)
            logging.info('{}:{}'.format(caps.Name, value))
        
    def auto_exp_compute_settings(self):
        """Camera needs some time to determine correct exposure value
        This will be handled in this section
        Method from https://github.com/python-zwoasi/python-zwoasi/blob/master/zwoasi/examples/zwoasi_demo.py
        """
        asi.ASIStartVideoCapture(self.info.CameraID)
        sleep_interval = 0.100
        df_last = None
        gain_last = None
        exposure_last = None
        matches = 0
        while True:
            time.sleep(sleep_interval)
            rtn, df = asi.ASIGetDroppedFrames(self.info.CameraID)
            rtn, exposure, _ = asi.ASIGetControlValue(self.info.CameraID, 1)
            if df != df_last:
                logging.debug('Exposure: {} Dropped frames: {}'.format(exposure,df))
            if exposure == exposure_last:
                matches += 1
            else:
                matches = 0
            if matches >= 5:
                # Record Exposure time
                self.exposure = exposure
                break
            df_last = df
            exposure_last = exposure
        asi.ASIStopVideoCapture(self.info.CameraID)
        logging.info('Stopped Video Capture\nExposure: {}'.format(exposure))

    
    def finish(self):
        out = asi.ASICloseCamera(self.info.CameraID)
        if out != asi.ASI_SUCCESS: logging.warning("Closing Camera Failed! {}".format(out))
        return None
    

    def capture_image_and_download(self, timeout = 100):
        if self.auto_exp: self.auto_exp_compute_settings()
        # What is bIsDark seems to be a boolean -- Dark images? -- seperate setting for this in sdk so dont know
        rtn = asi.ASIStartExposure(self.info.CameraID, bIsDark=False)
        if rtn != asi.ASI_SUCCESS: logging.error('Failed to initiate image exposure')
        start= time.time()
        while(1):
            ret, val = asi.ASIGetExpStatus(self.info.CameraID)
            # For some reason when it finishes it changes val from 1 to 2
            if val == 2:
                ret = asi.ASIStopExposure(self.info.CameraID)
                print('time taken for img (in python): ',  time.time()-start)
                break
            elif time.time() - start > 100:
                logging.error("Capture timed out")
                break

        if ret == asi.ASI_SUCCESS:
            # In c it expects nd unsigned char pointing to an image buffer and then also the buffer size
            # I assume the error refers to the wrong option
            rtn, out = asi.ASIGetDataAfterExp(self.info.CameraID, pBuffer=(3*self.info.MaxWidth*self.info.MaxHeight))
            print('Data return value: ',rtn)
            out = np.reshape(out, (self.info.MaxHeight,self.info.MaxWidth, 3))
            im = Image.fromarray(out)
            im_name = "{}.tiff".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
            im.save(im_name)
            # Get exposure value
            if self.auto_exp: exposure = self.exposure *1e-6 #microsec
            else: exposure = self.config['Exposure']
            # Now to write to the exif data
            # Common exif tags: https://exiftool.org/TagNames/EXIF.html
            # TODO: Add calibration matrices etc also take calibration matrices
            try: 
                # Raises exception if nonzero return code
                res = subprocess.check_output(['exiftool', '-ExposureTime={}'.format(exposure), '-ISO={}'.format(self.config['ISO']), 
                                            '-Model={}'.format(self.config['Model']),'-Make={}'.format(self.config['Brand']), im_name],stderr=subprocess.STDOUT)
                os.remove(im_name+'_original')
            except Exception as e:
                logging.error('Writing exif data to {} failed\nWriting data to log instead\nExposure:{}\nISO:{}\nError:{}'.format(im_name,exposure,self.config['ISO'],e))



class Camera_Handler_gphoto: #FIXME: Auto exposure check if Jake or Reynier know about setting -> otherwise write own code to set exposure by loading image after taking it with target max brightness 90%
    """Note that a lot of methods are implemented for camera control that arent used, that is just so the commands dont need to be searched for, odds are they wont directly work without more configuration"""
    def __init__(self, config_handler) -> None:
        # Check connected camera corresponds to config file specification

        self.config = config_handler.camera
        # Double checks brand and model
        self.find_camera() 
        ROOTLOGGER.info('Camera found')
        # Remove unwanted config settings and update camera internal settings for imaging routine
        config_subset = copy.deepcopy(self.config)
        
        config_subset.pop('Model')
        config_subset.pop('Brand')
        config_subset.pop('Image_Frequency')
        self.set_all_config_entries(config_subset)
        ROOTLOGGER.info('Set config entries')

        # Return camera internal settings for logging purposes
        self.get_camera_config()
        ROOTLOGGER.info('Camera configured to internal configuration:')
        print(self.internal_config)
        log_txt = ''
        for key in self.internal_config:
            log_txt+= f'{key}\n{self.internal_config[key][0]}\n{self.internal_config[key][1]}\n\n'
        ROOTLOGGER.info(log_txt)
        pass

    def find_camera(self):
        """Uses gphoto2 cmd line to find port and information about the camera connected to the system
        """
        # Check gphoto detects the correct camera -- assumes only 1 camera is detected 
        result = subprocess.run(["gphoto2 --auto-detect"], capture_output=True,check=True,shell=True)

        if not self.config['Brand'] in result.stdout.decode("utf-8").split('\n')[-2]:
            ROOTLOGGER.critical("Camera Brand mismatch")
            raise Exception('Camera Brand mismatch in gphoto2 auto detect, please fix the config file')
        else: pass

        if not self.config['Model'] in result.stdout.decode("utf-8").split('\n')[-2]:
            ROOTLOGGER.critical("Camera Model mismatch")
            raise Exception('Camera Model mismatch in gphoto2 auto detect, please fix the config file')
        else: pass

        return None
    
    def capture_image_and_download(self):
        """Captures an image with current settings and download"""
        ROOTLOGGER.info('Capturing and downloading Image')
        result = subprocess.run(['gphoto2 --capture-image-and-download --filename "%Y%m%d%H%M%S.cr2"'], capture_output=True,check=True,shell=True)
        if result.returncode != 0:
           ROOTLOGGER.critical("CMD: gphoto2 --capture-image-and-download")
           ROOTLOGGER.critical("Output: \n", result.stdout.decode("utf-8"))
           raise Exception('Capturing Image or downloading failed with the command output printed above')
        else: 
            ROOTLOGGER.info('Capture and download complete')

        return None
    

    def get_camera_config(self):
        """Returns camera internal configuration"""

        result = subprocess.run(["gphoto2 --list-all-config"], capture_output=True,check=True,shell=True)

        if result.returncode != 0:
           ROOTLOGGER.critical("CMD: gphoto2 --list-all-config")
           ROOTLOGGER.critical("Output: \n", result.stdout.decode("utf-8"))
           raise Exception('Retrieving camera config failed with the command output printed above')
        else:
            pass
        # Format output:
        out = result.stdout.decode("utf-8").split('\n')
        result = []
        # Filter out newline and Loading
        for i in out:
            if 'Loading' not in i:
                if '' != i:
                    result.append(i)

        out = {}
        in_cond = False

        for i in result:
            # Condition to note if iteration in entry or not
            # Verifies new entry
            if re.match('/*/*', i) is not None and not in_cond:
                in_cond = True
                config_path = i
            
            elif in_cond and "Label" in i:
                label = i

            elif in_cond and "Current" in i:
                current = i
            
            elif in_cond and i == "END":
                # Write settings to dictionary
                out[label] = [config_path, current]
                in_cond = False

            else:
                # Pass over other conditions
                pass

        self.internal_config = out

        return None
    
    
    def set_all_config_entries(self,config_dict):
        """Sets all relevant config entries for imaging iteratively
        ------
        config_dict --> dictionary with Key=Configentry:value=Configvalue
        """ 
        # Manual exposure setting (not required but remnant of first write up of the code)
        if config_dict['Exposure'] != 'Auto':
            config_dict['/main/capturesettings/shutterspeed'] = config_dict['Exposure']
            config_dict.pop("Exposure")
        else: #FIXME
            config_dict.pop("Exposure")
            # Set exposure mode to Fv so that Av is set minimum Tv (shutter speed) auto  (not sure what dial is but whatever)
            config_dict['/main/capturesettings/autoexposuremodedial'] = 34 # Fv
            config_dict['/main/capturesettings/autoexposuremode'] = 34 # Fv
            config_dict['/main/capturesettings/aperture'] = 1

        config_dict['/main/imgsettings/iso'] = config_dict['ISO'] # 
        config_dict.pop("ISO")
        config_dict['/main/imgsettings/imageformatsd'] = config_dict['Image_Format'] # 
        config_dict['/main/imgsettings/imageformat'] = config_dict['Image_Format'] # 
        config_dict.pop("Image_Format")

        for key in config_dict:
            self.set_config_entry(key,config_dict[key])
        
        return None


    def set_config_entry(self,entry, value):
        """Applies individual config"""
        result = subprocess.run(["gphoto2 --set-config {}={}".format(entry, value)], capture_output=True,check=True,shell=True)
        if result.returncode != 0:
           ROOTLOGGER.critical("CMD: gphoto2 --set-config-value {}={}".format(entry, value))
           ROOTLOGGER.critical("Output: \n", result.stdout.decode("utf-8"))
           raise Exception('Setting config value failed with the command output printed above')

        return None
    

    def finish(self):
        pass


class Camera_Handler_picamera:
    ctrl = {
            "AnalogueGain":1, 
            "AeEnable": False,  # Auto Exposure Value
            "AwbEnable":False,  # Auto White Balance
            "Brightness":0, # Default
            "ColourGains":(1.,1.), # Red and blue gains -> corresponds to as perceived
            "ExposureValue":0, # No exposure Val compensation --> Shouldnt be required as AeEnable:False
            "NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off, # No Noise reduction --> No idea how it works
            }
    auto_exp = False
    def __init__(self, config_handler) -> None:
        self.config = config_handler.camera
        # Create camera object with tuning file
        self.tuning = Picamera2.load_tuning_file(self.config['tuning_file'])
        self.camera = Picamera2(tuning=self.tuning)
        self.exp_limits =self.camera.sensor_modes[-1]['exposure_limits'] # (min,max, current)
        # Create capture config
        self.capture_config = self.camera.create_still_configuration(raw={})
        # Set ctrl settings
        self.set_up_camera()

    def set_up_camera(self):
        """Set settings"""
        if self.config['Exposure'] != 'Auto':
            self.ctrl['ExposureTime'] = self.config['Exposure']*1e6
        else: 
            # Make it auto set with agc algorithm but disable changes to iso 
            # Enable Auto exposure (algorithm aec/agc)
            self.ctrl['AeEnable'] = True
            # Get tuning algorithm for Ae # TODO Mod file itself
            agc = Picamera2.find_tuning_algo(self.tuning, "rpi.agc")
            # TODO: Try if this gain range works
            agc["exposure_modes"]["normal"] = {"shutter": [self.exp_limits[0], self.exp_limits[1]], "gain": [1.0,1.0]}
            # Set area for auto exposure if provided
            if 'AutoExpArea' in self.config:
                # TODO: Check bool is automatically convrted
                if self.config['AutoExpArea']:
                    # This refers to image areas, can be found here under rpi.agc https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf
                    # Here we focus fully on the central area TODO: Check if better to use px and check after imaging
                    agc["metering_modes"]['centre-weighted']['weights'] = [4 , 4 , 4 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0]
            self.auto_exp = True
        # Configure sensor mode etc
        self.camera.configure(self.capture_config)
        # Set other settings
        self.camera.set_controls(self.ctrl)
        


    def capture_image_and_download(self):
        """
        Starting and stopping camera occurs within this block to save on resouces
        As images wont be taken frequently
        """
        self.camera.start()
        if self.auto_exp:
            # Let it compute the exposure time TODO Check this works
            #self.camera.start_preview()
            time.sleep(3)

        im_name = "{}.dng".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        
        request = self.camera.capture_request()
        request.save_dng(im_name)
        # TODO: For spectroscope add option to check central area well enough exposed, maybe add HDR to increase sensitivity - remember px leakage
        self.camera.stop()

    def finish(self):
        self.camera.close()
    
"""Class that handles data transfer from local storage (most likely a rasberry pi) to the network storage"""
class File_Handler:
    def __init__(self,path_conf) -> None:
        # Define where images will be downloaded
        now = datetime.datetime.now()
        self.img_path = os.path.join(path_conf["FILE_SAVE"], now.strftime("%Y%m%d"))
        img_path = self.img_path
        # Logger set after directory created
        if not os.path.isdir(img_path) or len(os.listdir(img_path))==0:
            if not os.path.isdir(img_path):
                os.mkdir(img_path)
            ROOTLOGGER.info("Created save directory: {}".format(img_path))
        else:
            # Alternative handling if folder exists
            if len(os.listdir(img_path))>0:
                img_path = img_path+"_2"
                self.img_path = img_path
                if os.path.isdir(img_path):
                    raise Exception('Pipeline failed twice, investigate issue!')
                os.mkdir(img_path)
                with open(os.path.join(img_path,"dir_exists.txt"), 'w') as warn_file:
                    warn_file.write("Date directory existed already, using this directory to keep images from seperate runs seperated")
                    ROOTLOGGER.warning("File directory already exists: Using _2 directory")
            else:
                pass
        # Change path to download images into correct folder
        os.chdir(img_path)
        ROOTLOGGER.info("Changed working directory to {}".format(img_path))
        pass









"""Utility class to load and set config variables saved in INI formating using configparser, each attribute will be a dict containing the relevant data regarding each grouping"""
class Config_Handler:
    def __init__(self, path) -> None:
        # Load the config
        config = self.load_config(path)

        # Extract camera data
        self.camera = config["Camera"]

        # Check all relevant data present
        for i in ("Exposure", "ISO", "Image_Frequency", "Brand", "Model"):
            if i not in self.camera:
                raise Exception("Config file incomplete entry: {} missing".format(i))
            else:
                pass

        # Extract file paths
        self.paths = config["Paths"]

        self.location = config['Location']
        
        pass

    def load_config(self,path):
        config = cfg.ConfigParser()
        config.read(path)
        return config
    

if __name__=='__main__':
    main()