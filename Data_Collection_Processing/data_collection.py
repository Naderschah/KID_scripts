import configparser as cfg
import subprocess

"""Class that handles camera control, i.e. image taking 
Below is a list of backends and camera combinations that are to be used 
    gphoto2 (http://www.gphoto.org/proj/libgphoto2/support.php):
Canon 6D
Canon RP
    Note that for this backend I will not be using the python ported library but simply will execute the CMD line from within python

TODO; What camera did jake buy what backend can be used
"""

class Camera_Hanlder_jakes_thing:
    def __init__(self) -> None:
        pass


class Camera_Handler_gphoto:
    def __init__(self) -> None:
        # Check connected camera corresponds to config file specification
        self.find_camera()

        # Remove unwanted config settings and update camera internal settings for imaging routine
        config_subset = self.config
        config_subset.pop('Model')
        config_subset.pop('Brand')
        self.set_all_config_entries(config_subset)

        # Return camera internal settings for logging purposes
        self.get_camera_config()
        # TODO: change to logging module and pipe to some meta file
        print('Operation starting with camera internal configuration:')
        print(self.internal_config)

        pass

    def start_imaging():
        """Wrapper that does everything related to imaging"""

        # TODO:
        raise Exception('Not implemented')


    def get_camera_config():
        """Gets camera information"""
        
        config_handler = Config_Handler()
        self.config = config_handler.camera

        return None
    

    def find_camera():
        """Uses gphoto2 cmd line to find port and information about the camera connected to the system
        FIXME: Here I assumed that none of the cameras use RS232 to connect as it was a standard from the 1960s this should not raise any issues 
        """
        # Check gphoto detects the correct camera -- assumes only 1 camera is detected 
        result = subprocess.run(["gphoto2 --auto-detect"], capture_output=True)
        if not self.config['Brand'] in result.split('\n')[-1]:
            raise Exception('Camera Brand mismatch in gphoto2 auto detect, please fix the config file')
        elif not self.config['Model'] in result.split('\n')[-1]:
            raise Exception('Camera Model mismatch in gphoto2 auto detect, please fix the config file')
        
        return None
    
    def get_all_files():
        """Retrieves all files on sd card"""
        result = subprocess.run(["gphoto2 --get-all-files"], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --get-all-files")
           print("Output: \n", result)
           raise Exception('Downloading files failed with the command output printed above')
    
        return None
    
    def delete_all_files():
        """Deletes all files from sd card"""
        result = subprocess.run(["gphoto2 --delete-all-files"], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --delete-all-files")
           print("Output: \n", result)
           raise Exception('Deleting files failed with the command output printed above')
    
        return None
    
    def capture_image():
        """Captures an image with current settings"""
        result = subprocess.run(["gphoto2 --capture-image"], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --capture-image")
           print("Output: \n", result)
           raise Exception('Capturing Image failed with the command output printed above')
    
        return None
        
    
    def capture_image_and_download()
        """Captures an image with current settings and download"""
        result = subprocess.run(["gphoto2 --capture-image-and-download"], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --capture-image")
           print("Output: \n", result)
           raise Exception('Capturing Image or downloading failed with the command output printed above')
    
        return None
    

    def get_camera_config()
        """Returns camera internal configuration"""
        result = subprocess.run(["gphoto2 --list-all-config"], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --list-all-config")
           print("Output: \n", result)
           raise Exception('Retrieving camera config failed with the command output printed above')

        self.internal_config = result.stdout
        # TODO: Do formating

        return None
    
    
    def set_all_config_entries(config_dict):
        """Sets all relevant config entries for imaging iteratively
        ------
        config_dict --> dictionary with Key=Configentry:value=Configvalue
        """
        for key, value in config_dict:
            self.set_config_entry(key,value)
        
        return None


    def set_config_entry(entry, value):
        """Returns camera internal configuration"""
        result = subprocess.run(["gphoto2 --set-config {}={}".format(entry, value)], capture_output=True)
        if result.returncode != 0:
           print("CMD: gphoto2 --set-config {}={}".format(entry, value))
           print("Output: \n", result)
           raise Exception('Setting config value failed with the command output printed above')

        self.internal_config = result.stdout
        # TODO: Do formating

        return None




    
"""Class that handles data transfer from local storage (most likely a rasberry pi) to the network storage"""
class File_Handler:
    def __init__(self) -> None:
        pass

"""Class that handles data processing of previously saved images and saves output to whatever path is specified in the config"""
class Pipeline_Handler:
    def __init__(self) -> None:
        pass






"""Utility class to load and set config variables saved in INI formating using configparser, each attribute will be a dict containing the relevant data regarding each grouping"""
class Config_Handler:
    def __init__(self, path='./config.cfg') -> None:
        
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
        
        pass

    def load_config(path):
        config = cfg.ConfigParser()
        config.read(path)
        return config