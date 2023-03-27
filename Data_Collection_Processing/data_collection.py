import configparser as cfg
import subprocess
import os
import datetime
import suntime
import copy
import time
import logging
import re
import sys
import time
import numpy as np
from PIL import Image

"""Class that handles camera control, i.e. image taking 
Below is a list of backends and camera combinations that are to be used 
    gphoto2 (http://www.gphoto.org/proj/libgphoto2/support.php):
Canon 6D
Canon RP
    Note that for this backend I will not be using the python ported library but simply will execute the CMD line from within python
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

    # Check time to start
    sun = suntime.Sun(float(config.location['longitude']), float(config.location['latitude']))
    start = sun.get_sunset_time()
    end = sun.get_sunrise_time(datetime.datetime.now()+datetime.timedelta(days=1))

    ROOTLOGGER.info('Imaging start time: {} \nImaging stop time: {}'.format(start,end))

    while datetime.datetime.now(datetime.timezone.utc)<start and not DEBUG:
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
    main()





class Camera_Hanlder_ZWO: # FIXME: Autmatic Dark Subtraction - trial what it does?
    """Camera handler for ZWO devices
    """
    import asi  # No docs, mess around in python interactive to find commands 
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
        if self.config['Brand']+' '+self.config['Model'] != self.info["Name"]:
            logging.warning("Camera Brand mismatch! Expected {} Found {}".format(self.config['Brand']+' '+self.config['Model'] , self.info["Name"]))
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
                info.CameraID, 
                info.MaxWidth, # Img dim
                info.MaxHeight, # Img dim
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
        WB_R 2
        WB_B  ...
        Offset
        BandWidth
        Flip
        AutoExpMaxGain
        AutoExpMaxExpMS
        AutoExpTargetBrightness
        HardwareBin 10
        HighSpeedMode
        MonoBin
        Temperature
        GPS 14
        """
        config_subset = copy.deepcopy(self.config)
        
        config_subset.pop('Model')
        config_subset.pop('Brand')
        config_subset.pop('Image_Frequency')
        config_subset.pop('Image_Format')
        # Rename indexes
        config_subset[0] = config_subset['ISO'] 
        config_subset.pop('ISO')
        config_subset[1] = config_subset['Exposure'] 
        config_subset.pop('Exposure')


        for key,value in config_subset:
            # Params (cam id, control caps reference, value to bne set, bool autoadjust value)
            asi.ASISetControlValue(self.info.CameraID, asi.ASIGetControlCaps(self.info.CameraID, key), value, asi.ASI_FALSE)



        # Print to log file
        logging.info("Final Configuration:")
        rtn, num_controls = asi.ASIGetNumOfControls(self.info.CameraID)
        for control_index in range(num_controls):
            rtn, caps = asi.ASIGetControlCaps(self.info.CameraID, control_index)
            rtn, value, _ = asi.ASIGetControlValue(self.info.CameraID, caps.ControlType)
            logging.info('{}:{}'.format(caps.Name, value))
        

    
    def finish(self):
        out = asi.ASICloseCamera(self.info.CameraID)
        if out != asi.ASI_SUCCESS: logging.warning("Closing Camera Failed! {}".format(out))
        return None
    

    def capture_image_and_download(self, timeout = 100):
        # What the hell is bIsDark seems to be a boolean
        rtn = asi.ASIStartExposure(self.info.CameraID, bIsDark)
        if val != asi.ASI_SUCCESS: logging.error('Failed to initiate image exposure')
        # TODO: Finish fix 
        # How does this work --- find some C or python example script to understand --- docs are useless
        start = time.time()
        while(1):
            ret, val = asi.ASIGetExpStatus(self.info.CameraID)
            if val == asi.ASI_SUCCESS:
                ret = asi.ASIStopExposure(self.info.CameraID)
                break
            elif time.time() - start > 100:
                logging.error("Capture timed out")
                break

        if ret == asi.ASI_SUCCESS:
            # Figure out pBuffer : errror on string says: Int Dimension expected
            # In c it expects nd unsigned char pointing to an image buffer and then also the buffer size
            # I assume the error refers to the wrong option
            rtn, out = asi.ASIGetDataAfterExp(self.info.CameraID, pBuffer=(self.info.MaxWidth*self.info.MaxHeight))
            out = np.reshape(out, (self.info.MaxWidth,self.info.MaxHeight))
            im = Image.fromarray(out)
            im.save("{}.tiff".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S")))



class Camera_Handler_gphoto:
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

        config_dict['/main/capturesettings/shutterspeed'] = config_dict['Exposure']
        config_dict.pop("Exposure")
        config_dict['/main/imgsettings/iso'] = config_dict['ISO'] # 
        config_dict.pop("ISO")
        config_dict['/main/imgsettings/imageformatsd'] = config_dict['Image_Format'] # 
        config_dict['/main/imgsettings/imageformat'] = config_dict['Image_Format'] # 
        config_dict.pop("Image_Format")

        for key in config_dict:
            self.set_config_entry(key,config_dict[key])
        
        return None


    def set_config_entry(self,entry, value):
        """Returns camera internal configuration"""
        result = subprocess.run(["gphoto2 --set-config {}={}".format(entry, value)], capture_output=True,check=True,shell=True)
        if result.returncode != 0:
           ROOTLOGGER.critical("CMD: gphoto2 --set-config-value {}={}".format(entry, value))
           ROOTLOGGER.critical("Output: \n", result.stdout.decode("utf-8"))
           raise Exception('Setting config value failed with the command output printed above')

        return None
    
    def finish(self):
        pass




    
"""Class that handles data transfer from local storage (most likely a rasberry pi) to the network storage"""
class File_Handler:
    def __init__(self,path_conf) -> None:
        # Define where images will be downloaded
        now = datetime.datetime.now()
        img_path = os.path.join(path_conf["FILE_SAVE"], now.strftime("%Y%m%d"))
        # Logger set after directory created
        if not os.path.isdir(img_path) or len(os.listdir(img_path))==0:
            if not os.path.isdir(img_path):
                os.mkdir(img_path)
            ROOTLOGGER.info("Created save directory: {}".format(img_path))
        else:
            # Alternative handling if folder exists
            if len(os.listdir(img_path))>0:
                img_path = img_path+"_2"
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





"""Class that handles data processing of previously saved images and saves output to whatever path is specified in the config"""
class Pipeline_Handler:
    def __init__(self) -> None:
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

        # Check all relevant data present
        #TODO What data is required

        # Extract pipeline executable command
        self.pipeline = config["Pipeline"]

        # Check pipeline exists
        #TODO Prob not gonna be required here

        self.location = config['Location']
        
        pass

    def load_config(self,path):
        config = cfg.ConfigParser()
        config.read(path)
        return config
    

if __name__=='__main__':
    main()