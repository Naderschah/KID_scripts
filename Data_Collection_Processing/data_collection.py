import configparser as cfg
import subprocess
import os
import datetime
import suntime
import time

"""Class that handles camera control, i.e. image taking 
Below is a list of backends and camera combinations that are to be used 
    gphoto2 (http://www.gphoto.org/proj/libgphoto2/support.php):
Canon 6D
Canon RP
    Note that for this backend I will not be using the python ported library but simply will execute the CMD line from within python

TODO; What camera did jake buy what backend can be used
"""




def main():
    # TODO; Iterate per night

    # Sets up folder for night and switches directory
    file_handler = File_Handler()    
    # Retrieve config file
    config = Config_Handler(path=os.path.join(os.path.abspath(os.getcwd()),'config.in'))
    # Set up camera control - each init will check the correct camera and brand is 
    if config.camera['Brand'] in ["Canon", "Nikon"]: # Add the other ones if required
        camera = Camera_Handler_gphoto(config)
    elif config.camera['Brand'] == "Jakes thing": # TODO:
        camera = Camera_Hanlder_jakes_thing(config)

    # Check time to start
    sun = suntime.Sun(config.location['longitude'], config.location['latitude'])
    start = sun.get_sunset_time()
    end = sun.get_sunrise_time(datetime.datetime.now()+datetime.timedelta(days=1))

    while datetime.datetime.now()<start:
        time.sleep(15*60) # 15 minutes 

    while datetime.datetime.now()<end:
        camera.capture_image_and_download()
        time.sleep(config.camera['Image_Frequency']*60)
        



class Camera_Hanlder_jakes_thing:
    def __init__(self) -> None:
        pass


class Camera_Handler_gphoto:
    def __init__(self, config_handler) -> None:
        # Check connected camera corresponds to config file specification

        self.config = config_handler.camera
        # Double checks brand and model
        self.find_camera() # TODO: 
        
        # Remove unwanted config settings and update camera internal settings for imaging routine
        config_subset = self.config
        
        config_subset.pop('Model')
        config_subset.pop('Brand')
        config_subset.pop('Image_Frequency')
        # TODO: uncomment below
        #self.set_all_config_entries(config_subset)

        # Return camera internal settings for logging purposes
        self.get_camera_config()
        # TODO: change to logging module and pipe to some meta file
        print('Camera configured to internal configuration:')
        print(self.internal_config)

        pass

    def find_camera(self):
        """Uses gphoto2 cmd line to find port and information about the camera connected to the system
        FIXME: Here I assumed that none of the cameras use RS232 to connect as it was a standard from the 1960s this should not raise any issues, also assume only 1 camera
        """
        # Check gphoto detects the correct camera -- assumes only 1 camera is detected 
        result = subprocess.run(["gphoto2 --auto-detect"], capture_output=True)

        if not self.config['Brand'] in result.split('\n')[-1]:
            raise Exception('Camera Brand mismatch in gphoto2 auto detect, please fix the config file')
        else: pass

        if not self.config['Model'] in result.split('\n')[-1]:
            raise Exception('Camera Model mismatch in gphoto2 auto detect, please fix the config file')
        else: pass

        return None
    
    def get_all_files(self):
        """Retrieves all files on sd card"""
        result = subprocess.run(["gphoto2 --get-all-files"], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --get-all-files")
           print("Output: \n", result)
           raise Exception('Downloading files failed with the command output printed above')
    
        return None
    
    def delete_all_files(self):
        """Deletes all files from sd card"""
        result = subprocess.run(["gphoto2 --delete-all-files"], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --delete-all-files")
           print("Output: \n", result)
           raise Exception('Deleting files failed with the command output printed above')
    
        return None
    
    def capture_image(self):
        """Captures an image with current settings"""
        result = subprocess.run(["gphoto2 --capture-image"], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --capture-image")
           print("Output: \n", result)
           raise Exception('Capturing Image failed with the command output printed above')
    
        return None
        
    
    def capture_image_and_download(self):
        """Captures an image with current settings and download"""
        result = subprocess.run(["gphoto2 --capture-image-and-download"], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --capture-image")
           print("Output: \n", result)
           raise Exception('Capturing Image or downloading failed with the command output printed above')
    
        return None
    

    def get_camera_config(self):
        """Returns camera internal configuration"""

        result = subprocess.run(["gphoto2 --list-all-config"], capture_output=True)

        if result.returncode != 0:
           print("CMD: gphoto2 --list-all-config")
           print("Output: \n", result)
           raise Exception('Retrieving camera config failed with the command output printed above')
        else:
            pass

        self.internal_config = result.stdout
        # TODO: Do formating

        return None
    
    
    def set_all_config_entries(self,config_dict):
        """Sets all relevant config entries for imaging iteratively
        ------
        config_dict --> dictionary with Key=Configentry:value=Configvalue
        """ # TODO; this wont work

        config_dict['Shutter Speed'] = config_dict['Exposure']
        config_dict['ISO Speed'] = config_dict['Exposure']
        for key, value in config_dict:
            self.set_config_entry(key,value)
        
        return None


    def set_config_entry(self,entry, value):
        """Returns camera internal configuration"""
        result = subprocess.run(["gphoto2 --set-config {}={}".format(entry, value)], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --set-config {}={}".format(entry, value))
           print("Output: \n", result)
           raise Exception('Setting config value failed with the command output printed above')

        return None




    
"""Class that handles data transfer from local storage (most likely a rasberry pi) to the network storage"""
class File_Handler:
    def __init__(self) -> None:
        # Define where images will be downlaoded
        now = datetime.datetime.now()
        img_path = os.path.join(os.path.abspath('~'), now.strftime("%Y%m%d"))
        if not os.path.isdir(img_path):
            os.mkdir(img_path)
        else:
            # Alternative handlign if folder exists
            if len(os.listdir(img_path))>1:
                img_path = img_path+"_2"
                with open("dir_exists.txt") as warn_file:
                    warn_file.write("Date directory existed already, using this directory to keep images from seperate runs seperated")
            else:
                pass
        # Change path to download images into correct folder
        os.chdir(img_path)

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
        #TODO

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