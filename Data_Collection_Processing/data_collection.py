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

"""Class that handles camera control, i.e. image taking 
Below is a list of backends and camera combinations that are to be used 
    gphoto2 (http://www.gphoto.org/proj/libgphoto2/support.php):
Canon 6D
Canon RP
    Note that for this backend I will not be using the python ported library but simply will execute the CMD line from within python

TODO; What camera did jake buy what backend can be used
FIXME: IO error (camera --> find out why happens , raspberry --> do file management)
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

# Setting gphoto file config
if os.path.isdir('/home/raspberry/.gphoto'):
    os.remove('/home/raspberry/.gphoto/settings')
else:
    os.mkdir('/home/raspberry/.gphoto')

with open('/home/raspberry/.gphoto/settings','w') as file_:
    # Set file name convention otherwise failes onwrite asking if user wants to overwrite
    file_.write('gphoto2=filename=%Y%m%d-%H:%M:%S.jpg')
    # The rest of the file will be populated by auto detect




def main():
    print('setting up config')
    # Retrieve config file
    config = Config_Handler(path=os.path.join(CODE_DIR,'config.ini'))

    # Sets up folder for night and switches directory
    print('setting up file handler')
    file_handler = File_Handler(config.paths)
    # Set up camera control - each init will check the correct camera and brand is 
    print('Configure camera')
    if config.camera['Brand'] in ["Canon", "Nikon"]: # Add the other ones if required
        ROOTLOGGER.info("Using gphoto2 as backend")
        camera = Camera_Handler_gphoto(config)
    elif config.camera['Brand'] == "Jakes thing": # TODO:
        ROOTLOGGER.info("Using some other backend")
        camera = Camera_Hanlder_jakes_thing(config)

    print('Getting operation times')
    # Check time to start
    sun = suntime.Sun(float(config.location['longitude']), float(config.location['latitude']))
    start = sun.get_sunset_time()
    end = sun.get_sunrise_time(datetime.datetime.now()+datetime.timedelta(days=1))

    ROOTLOGGER.info('Imaging start time: {} \nImaging stop time: {}'.format(start,end))
    print('Imaging start time: {} \nImaging stop time: {}'.format(start,end))

    while datetime.datetime.now(datetime.timezone.utc)<start and not DEBUG:
        ROOTLOGGER.info("Waiting for night")
        print("Waiting for night")
        time.sleep((start-datetime.datetime.now(datetime.timezone.utc)).total_seconds())
    ROOTLOGGER.info('Starting Imaging')
    print('Starting Imaging')
    counter = 1
    while datetime.datetime.now(datetime.timezone.utc)<end:
        print('Taking image ', counter)
        camera.capture_image_and_download()
        time.sleep(int(config.camera['Image_Frequency'])*60)
        counter += 1
    print('Total Images ', counter)
    ROOTLOGGER.info('Total number of images ', counter)

    main()





class Camera_Hanlder_jakes_thing:
    def __init__(self,config_handler) -> None:
        self.config = config_handler.camera
        pass


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
        for key in self.internal_config:
            ROOTLOGGER.info('{key}\n{self.internal_config[key][0]}\n{self.internal_config[key][1]}\n\n')

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
    
    def get_all_files(self):
        """Retrieves all files on sd card"""
        result = subprocess.run(["gphoto2 --get-all-files"], capture_output=True,check=True,shell=True)
        if result.returncode != 0:
           ROOTLOGGER.critical("CMD: gphoto2 --get-all-files")
           ROOTLOGGER.critical("Output: \n", result.stdout.decode("utf-8"))
           raise Exception('Downloading files failed with the command output printed above')
    
        return None
    
    def delete_all_files(self):
        """Deletes all files from sd card"""
        result = subprocess.run(["gphoto2 --delete-all-files"], capture_output=True,check=True,shell=True)
        if result.returncode != 0:
           ROOTLOGGER.critical("CMD: gphoto2 --delete-all-files")
           ROOTLOGGER.critical("Output: \n", result.stdout.decode("utf-8"))
           raise Exception('Deleting files failed with the command output printed above')
    
        return None
    
    def capture_image(self):
        """Captures an image with current settings"""
        result = subprocess.run(["gphoto2 --capture-image"], capture_output=True,check=True,shell=True)
        if result.returncode != 0:
           ROOTLOGGER.critical("CMD: gphoto2 --capture-image")
           ROOTLOGGER.critical("Output: \n", result.stdout.decode("utf-8"))
           raise Exception('Capturing Image failed with the command output printed above')
    
        return None
        
    
    def capture_image_and_download(self):
        """Captures an image with current settings and download"""
        ROOTLOGGER.info('Capturing and downloading Image')
        result = subprocess.run(["gphoto2 --capture-image-and-download"], capture_output=True,check=True,shell=True)
        if result.returncode != 0:
           ROOTLOGGER.critical("CMD: gphoto2 --capture-image-and-download")
           ROOTLOGGER.critical("Output: \n", result.stdout.decode("utf-8"))
           raise Exception('Capturing Image or downloading failed with the command output printed above')
        else: 
            ROOTLOGGER.info('Capture and downlaod complete')

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
        for i in result:
            # Condition to note if iteration in entry or not
            in_cond = False
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




    
"""Class that handles data transfer from local storage (most likely a rasberry pi) to the network storage"""
class File_Handler:
    def __init__(self,path_conf) -> None:
        # Define where images will be downlaoded
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
        #TODO

        # Extract pipeline executable command
        self.pipeline = config["Pipeline"]

        # Check pipeline exists
        #TODO

        self.location = config['Location']
        
        pass

    def load_config(self,path):
        config = cfg.ConfigParser()
        config.read(path)
        return config
    

if __name__=='__main__':
    main()