import configparser as cfg
import subprocess
import os
import datetime
# pip library module to determine sunrise suntime - think civil but ont sure defenitely not astronomical 
import suntime
import copy
import time
import logging
import re
import time
import numpy as np
# Image handling -- can handle images with bit depth larger than 8 -- note python only supports 8 and 16 so arrays will prob be saved with 16 but actual depth will be different -- just chekc max vals on well exposed image or make one way overexposed one and check what max val is to determine
from PIL import Image
import tarfile
import subprocess
import json
# To interface with the raspberries gpio pins
import RPi.GPIO as GPIO
import sys

try: # ASI ZWO SDK library python SWIG port 
    import asi
except:
    pass

try: # picamra backend should never go to except cause part of raspbian for a few years now 
    from picamera2 import Picamera2, Preview, Controls
    from libcamera import controls
except:
    pass
# Change to false for actual imaging, true to ignore imaging times and jsut start 
DEBUG = False


"""
The config file  for imaging is expected to be called have config in its name 
and end in .ini while being in the same directory as this script file
As long as config is in it and it ends in ini it is recognized (first occurance selected)

DEBUG parameter tells the script to not wait for nighttime but just start imaging

When running a logfile will be created in working_dir/logs/YYmmdd.log 
I am not sure if this works realibly python logging is always hacky from my experience
So most things are also printed to stdout which if run with teh cronjob will be redirected to ~/Imageing_Output.txt

I will now outline the generic pattern of the code by which it operates, after I will give  an overview of the individual class structures
I did not make one parent class as all backends require their own little ideas but there are some methods new classes muyst implement to be compatible with the code

Global declaration:
Logging:
    First directory parsing to create the logger and creates relevant directories
    The logger object is ROOTLOGGER with file interface fileHandler

main():
    source config file 
    if not named config.ini searches working directory 
    Ends with config = Config_Handler(...) for explanation of this go to the class explanation below 

    Next the correct backend handler class is selected based on camera brand 
    - gphoto for canon/nikon (cmd line not python port)
    - zwoasi for zwo 
    - PiCamera2 for raspbery based cameras 
    If the config file specifies a moving camera the motor backend is initiated

    Next start and stopping times for imaging are parsed, herre the DEBUG parameter takes effect 

    In a while True loop the seconds until variable start are waited on the second iteration the while loop will temrinate
    - while True is not really required as it will always evaluate to false on the second run

    If a motor is in use now a list will be created with the angles at which the camera will view
     - simply iterated append - wanted to stay away from non pure python types (ndarray) as much as possible to avoid typing issues

    Next the file handler is initiated creating the working directory -- originally did so before waiting but for some stations prefereable to create jsut before imaging 

    Starts imaging loop for time < sunrise_time :: Sunrise time i think is civil but i didnt want to write the code to compute astronomical 

    If motor is attached moves to relevant coordinate then calls imaging method of camera-handler class created earlier
    
    Then sleeps time specified by frequency parameter of config file --> note the actual imaging frequency is -> imgtime+ img_freq_conf 

    At the end of the night it steps out of the loop prints total number of images 
    
    then makes a tarball of the images --> I was asked to leave the originals as well 
    
    calls the camera closing method if required 

    and restarts main()

main is executed in if __name__=="__main__":\n main() \n return

Backend camera handlers: Camera_Handler_ZWO, Camera_Handler_gphoto, Camera_Handler_picamera

Basic functions required in each  for main
 self.__init__ : obv. sets up all the things
 self.capture_image_and_download(pass_meta) : Pass_meta --> extra info to be passed to exif data -> used for picamera rotation otherwise ignored at the moment 
 self.finish() : Closes all interfaces and puts camera to "sleep", jsut finishing sequence so that after restart (of anything) the class can init again

All methods and variables implemented in each:
    Camera_Handler_ZWO:
        -var : controls :: Dict -> contains all controls associated with the camera, each object will be addded during execution each will be a swig object (C code port to python )
        -var : error_codes :: Dict -> contains num rep and corresponding error code of the underlying C library 
        -var : auto_exp :: Bool -> In case auto exposure should be enabled each class has this or somethin like this for internal handling
        -method : __init__(slef,config_handler) :: ret None -> checks cameras connected and corresponds to teh one specified in the logfile, calls methods in order: set_up_camera(),get_controls(), set_controls()
        -method : set_up_camera(self) : Opens camera stream, inits camera, sets video mode with ROI -> this was some linked behavior that doesnt make sense when read pythonically --> dont mess with it or be ready to do lots of debugging to understand
        -method : get_controls(self) :: ret None : Grabs all control sequence swig objects  to be added to earlier defined var
        -method : set_controls(self):: ret None : In func docstring all controls are layed out with numeric value sets them according to config file --> Jake fixed auto exp parameters consult him about it 
        -method : auto_exp_compute_settings :: ret None : Waits for exposure to be adjusted for current working conditions 
        -method : finish :: ret None : closes camrea interface 
        -method : capture_image_and_download(self, timeout=100, pass_meta=None) :: ret None : Starts exposure waits for success for exposure time reached reshapes data array and saves as tiff (with bits spec by image) adds basic info into exif data with exiftools 
    Camera_Handler_gphoto -- no real closing and opening happening it just kind of is on all the time 
      Also this isnt used we use the germans scripts
        -method : __init__ : Grabs all parameters required from config, grabs camrea configuration sets all config  from connected camera szstems prints all to logfile 
        -method : find_camera: verifies config file entrz with data from connected camera 
        -method : capture_image_and_download(self,pass_meta) : runs gphoto2 --capture-image-and-download with subprocess -- checks output -- blocking
        -method : get_camera_config : runs gphoto2 --list-all-config and parses the output adds this to self.internal_config
        -method : set_all_config_entries(config_dict) : Sets all config entries found in config_dict
        -method : set_config_entry(self,entry,value) : Appleis individual config entries - helper class for above
        -method : finish :: As no finishing behavior is required it just passes 
    Camera_Handler_picamera :
        -var ctrl : dict of parameters to be set into camrea config so that the ISP doesnt mess with the images this should be the maximum possible before messing witht the tuning fiel -- something we cant avoid happening on the other two systems (or rather dont actually know if they mess with it or not)
        -var auto_exp : If auto exposure should be used 
        ßmethod : __init__(self, config_handler): ret None : For some reason i made it create the config_handler if not present so does what main config seatrching does
                        - then it retrieves the tuning file for the ISP changes everzthing that modifies the images in any way so that we only get the raw data take a look at the tuning documentation to understand whats going on here 
                        - then initializes the camera object with the tuning file (copies it over to the ISP )
                        - set operational configuration for camera (before was board level)
                        - retrieve oeprational parameteres : bit depth exp resolution etc
                        - set the third level of configuration  (dont know what to call it just stuff that can be changed when the camera is operating like exposure iso and whatnot)
        -method : set_up_camera : last line of init sets operational configuration (ISO exp whatever)
        -method : capture_image_and_download(self, name, check_max, pass_meta ): No areguments are required most are for spectroscope extensions
                    - starts camera : If autoexp waits until camera doesnt change exposure anymore creates apture request and blocks until data arrives, modifies metadata.json file storing each images metadata (faster than constantly using exiftools - annoying to call nonblocking as well) note the whole seek mechanic is so that the json can be quickly modified without requiring to read in the entire file 
                    - now saves dng file (adobe digital negative - rawpy can open gimp can open darktable can open any adobe thing can open ) releases request back to camera board has optional hdr (never used caus was intended for spectroscope ) this is a shitty version essentially take a few images at different exposures and then use that the 20-80% exp valeus will be more sensitive than the others to get a bit more sensitivity at a few more ranges 
                    - then stops camera if check_max_thresh is active it checks how much of the image has maximum valeu --- seems wrong to me now cause 255 but should be variable with bps soo: 2^bps-1
        -method: set_controls(self,wait=True) :  Sets controls as specified by config file class also keeps track in self.ctrl then waits for changes to be recognized
        -method: determine_exp : Determines required exposure from image and exposure used for spectroscope so not in use -- still missing things cause response nonlinear right now linear so long time to converge 
        -method: take_bias(num_im=50, Gain=1) : Takes num_im bias images with specified gain (shortest exp possible without div null error) gain can also be list to take several for different gains
        -method : take_darks : args num_im exp gain same as take_bias but darks
        -method : finish : closes camera object

Motor Class:
    MotorController_ULN2003
        - var step_sequence: sequence of signals to send for each ms pin used to locate where the current chain is and what the next pin sequence is
        - var stp_counter : counts steps since initialization
        - var deg_per_step : degree step conversion constant 
        - var total_angle : like stp_counter but in degrees 
        - var dir : bool : true is forward in step_list false is backwards
        -method __init__ (gpio, delay=0.01, name='azi') : gpio corresponds to ms pins in order (list ), delay corresponds to the time delay between individual steps (required so that the motor actually can move) name gives name for file in /home/motor_<name>.curr_rot -- this file needs to be precreated and permissions need to be fixed
                sets the gpio modes and general boilerplate for gpio gets total rot angle from the file if present 
        - method : move_to_angle(self,angle) : Moves  to angle relative to zeropoint (ie rotation at which the file says 0 - this is  a stepper motor so doesnt have a rotary encoder) - note that the angle shoudl never be negative as it makes construction easier, ie when first starting the script make sure the motor is at its zeropoint 
        - change_dir : changes direction boolean -- not really required but for oop good form
        - step_angle : steps specified angle in current direction returns actual angle stepped due to step discretization
        - step : steps step_count times and writes steps to file at teh end 

Now to the utility classes 
    File_Handler --- this was kind of not required
    - method : __init__(self,path_conf)  creates the file structure path_conf corresponds to the config handlers path subsection
            If the working directory for image saving exists it will create it with _2 if that also exists it will call sys.exit(0) saying that something is wrong, ignored in DEBUG 
    Thats all this does, making a class was a bit overkill

    Config_Handler: 
    -method : __init__(self,path) : loads config from path, extracts into self.camera all camera related entries, checks all camera required things are present, extracts motor related things into self.MotorAzi (for motor alt a sepereate variable needs to be added here), does the same with paths, location
    - method: load_config(self,path) : loads the config file with pythons standard library cfg library reutrns parsed content
    -- Again could have been a function but originally though this (and file_handler) would play more dominant roles 

Thats it
"""


# Logging set up

### IMPORTANT: I do not get how loggers work, I have had only inconsistent reults this may need reworking
CODE_DIR = os.path.abspath(os.getcwd())
# Code Dir and File dir mustnt overlap
FILE_DIR = os.path.abspath(__file__)
FILE_PARENT = '/'+'/'.join(FILE_DIR.split('/')[:-1:])+'/'

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


# All code hosted in here, run at EOF with: if __name__=='__main__'
def main():
    # Retrieve config file
    config_path = os.path.join(CODE_DIR,'config.ini')

    # Check for some config file
    if os.path.isfile(config_path):
        pass
    else:
        fl = os.listdir(FILE_PARENT)
        bool_fl = ['config' in i and i.endswith('.ini') for i in fl]
        if sum(bool_fl)>1 or sum(bool_fl)==0:
            print('Fix the config file\nIt needs to be in the same directory as the script and have config in its name and end in .ini')
        filen = [fl[i] for i in range(len(fl)) if bool_fl[i]]
        if len(filen)==0:
            raise Exception('Config File not Found')
        config_path = os.path.join(FILE_PARENT,filen[0])
    
    config = Config_Handler(path=config_path)

    
    # Set up camera control - each init will check the correct camera and brand is 
    if config.camera['Brand'] in ["Canon", "Nikon"]: # Add the other ones if required
        ROOTLOGGER.info("Using gphoto2 as backend")
        camera = Camera_Handler_gphoto(config)
    elif config.camera['Brand'] == "ZWO": 
        ROOTLOGGER.info("Using zwo asi sdk backend (not sure what asi stands for)")
        camera = Camera_Hanlder_ZWO(config)
    elif config.camera['Brand'] in ["PiCamera", 'Arducam', 'Waveshare']: 
        ROOTLOGGER.info("Using picamera backend")
        camera = Camera_Handler_picamera(config)

    motor_azi_bool = False
    if hasattr(config, 'MotorAzi'):
        print('Initiating Motor')
        motor_azi = MotorController_ULN2003(gpio = [int(config.MotorAzi['ms1']),int(config.MotorAzi['ms2']),int(config.MotorAzi['ms3']),int(config.MotorAzi['ms4'])])
        # Variable to check later if this is required
        motor_azi_bool = True # TODO Track total angle in camera to add to config 

    # Check time to start
    if not DEBUG:
        sun = suntime.Sun(float(config.location['longitude']), float(config.location['latitude']))
        start = sun.get_sunset_time()
        end = sun.get_sunrise_time(datetime.datetime.now()+datetime.timedelta(days=1))
    else:
        start = datetime.datetime.now(datetime.timezone.utc)
        end = start+datetime.timedelta(days=1)

    ROOTLOGGER.info('Imaging start time: {} \nImaging stop time: {}'.format(start,end))
    # Wait for night 
    while datetime.datetime.now(datetime.timezone.utc)<start:
        ROOTLOGGER.info("Waiting for night")
        print("Waiting for night")
        time.sleep((start-datetime.datetime.now(datetime.timezone.utc)).total_seconds())
    ROOTLOGGER.info('Starting Imaging')
    counter = 1
    # Generatre coordinate array if motor connected 
    if motor_azi_bool:
        azi_coords = []
        i =0
        while i <= 360-int(config.MotorAzi['step_size']):
            azi_coords.append(i)
            i += int(config.MotorAzi['step_size'])
        if azi_coords[-1] != 360-int(config.MotorAzi['step_size']):
            azi_coords.append(360-int(config.MotorAzi['step_size']))
            # Booleans for later list iteration
        azi_coord_index = 0
        azi_up = True
        print('Azi Coordinate list')
        print(azi_coords)
    
    
    # Sets up folder for night and switches directory -- moved here in case cleanup is done throughout the day
    file_handler = File_Handler(config.paths)
    # Start imaging
    while datetime.datetime.now(datetime.timezone.utc)<end:
        print('Starting imaging ', counter)
        # Used to store motor ratation in exif data (or metadatafile depending on backend)
        ext_meta = {}
        # Move motor
        if motor_azi_bool:
            print('Moving to angle: {}'.format(azi_coords[azi_coord_index]))
            motor_azi.move_to_angle(azi_coords[azi_coord_index])
            #Check if iteration direction needs changing
            if azi_coords[azi_coord_index] == azi_coords[-1]:
                azi_up = False
            elif azi_coords[azi_coord_index] == azi_coords[0]:
                azi_up = True
            # Set next index
            if azi_up:
                azi_coord_index += 1
            else:
                azi_coord_index -= 1
            ext_meta['azi_angle'] = motor_azi.total_angle
            print('Motor at {} deg rotation relative to start point'.format(ext_meta['azi_angle']))
        # Camera do image 
        camera.capture_image_and_download(pass_meta=ext_meta)
        counter += 1
        # Wait for next 
        time.sleep(int(config.camera['Image_Frequency'])*60)
        # Repeat
    ROOTLOGGER.info('Total number of images {}'.format(counter))
    # The below is for cameras that require closing at the end of the night
    camera.finish()
    # Now we also compress the created data
    with tarfile.open(file_handler.img_path.split('/')[-1]+'.tar.gz', "w:gz") as tar:
        tar.add(file_handler.img_path, arcname=os.path.basename(file_handler.img_path))
    # When we decide to remove original files move the tarball into the parent directory of where its at now (cause rn it lives with the images rather than above it)
    # Then uncomment below to delte the entire image path so that the tarball is the onlything that survives
    #os.remove(file_handler.img_path)
    # Restart
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
            # Sets AutoExpMaxGain to some random number cause i dont know the maximum
            asi.ASISetControlValue(self.info.CameraID, 10, 10, asi.ASI_TRUE)
            # Sets AutoExpMaxExpMS to maximum of 1000s == 1000000 mus
            asi.ASISetControlValue(self.info.CameraID, 11, 1000000, asi.ASI_TRUE)
            # Sets AutoExpTargetBrightness to 100
            asi.ASISetControlValue(self.info.CameraID, 12, 2000, asi.ASI_TRUE)
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
    

    def capture_image_and_download(self, timeout = 100, pass_meta=None):
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
    
    def capture_image_and_download(self, pass_meta=None):
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
            "AeMeteringMode":controls.AeMeteringModeEnum.CentreWeighted,
            'AeExposureMode':controls.AeExposureModeEnum.Normal,
            }
    auto_exp = False
    def __init__(self, config_handler=None) -> None:
        if config_handler is not None:
            self.config = config_handler.camera
        else:
            config_path = os.path.join(CODE_DIR,'config.ini')

            # Check for some config file
            if os.path.isfile(config_path):
                pass
            else:
                fl = os.listdir(FILE_PARENT)
                bool_fl = ['config' in i and i.endswith('.ini') for i in fl]
                if sum(bool_fl)>1 or sum(bool_fl)==0:
                    print('Fix the config file\nIt needs to be in the same directory as the script and have config in its name and end in .ini')
                filen = [fl[i] for i in range(len(fl)) if bool_fl[i]]
                if len(filen)==0:
                    raise Exception('Config File not Found')
                config_path = os.path.join(FILE_PARENT,filen[0])
            
            self.config = Config_Handler(path=config_path).camera
        # Create camera object with tuning file
        ROOTLOGGER.info('Loading tuning file: {}'.format(self.config['Tuning_File']))
        self.tuning = Picamera2.load_tuning_file(self.config['Tuning_File'])
        # Get exposure limits
        # Overwrite tuning file parameters
        self.tuning['algorithms'][0]['rpi.black_level']['black_level'] = 0
        self.tuning['algorithms'][4]['rpi.geq']['offset'] = 0
        self.tuning['algorithms'][4]['rpi.geq']['slope'] = 0
        if 'Spectro_Metering' in self.config:  
            if self.config['Spectro_Metering']: # FIXME: Check this works otherwise scrap and do manually
                ROOTLOGGER.info('Using Spectroscope Metering') # TODO Change metering in ctrls
                # Each number represents a section of the image
                self.tuning['algorithms'][7]['rpi.agc']['metering_modes']['centre-weighted']['weights'] = [4 , 4 , 4 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0 , 0]
            # Always use 1 gain
            self.tuning['algorithms'][7]['rpi.agc']['exposure_modes']['normal']['gain'] = [1]*len(self.tuning['algorithms'][7]['rpi.agc']['exposure_modes']['normal']['gain'])
        # luminance 0 disables algorithms effect
        self.tuning['algorithms'][8]['rpi.alsc']["luminance_strength"] = 0
        # Reduce load on isp
        self.tuning['algorithms'][8]['rpi.alsc']["n_iter"] = 1
        # Disable gamma curve
        self.tuning['algorithms'][9]['rpi.contrast']["ce_enable"] = 0
        # Tuning file sometimes has sharpen and ccm swapped 
        if 'rpi.ccm' in self.tuning['algorithms'][10]: index = 10 #TODO : Make all independent of index
        elif 'rpi.ccm' in self.tuning['algorithms'][11]: index = 11

        # Disable color correction matrix for all color temperatures
        for i in range(len(self.tuning['algorithms'][index]['rpi.ccm']['ccms'])):
            self.tuning['algorithms'][index]['rpi.ccm']['ccms'][i]['ccm'] = [1,0,0,0,1,0,0,0,1]

        self.camera = Picamera2(tuning=self.tuning)
        # The below property might change through imaging so keep true
        self.sensor_modes = self.camera.sensor_modes
        self.exp_limits =self.sensor_modes[-1]['exposure_limits'] # (min,max, current)
        self.gain_limts = self.camera.camera_controls['AnalogueGain']
        # Get img output bit depth
        self.bit_depth = self.camera.sensor_modes[-1]['bit_depth']
        # Create capture config - > Note the raw stream config rather than just passing the appropriate sensor mode, theere is some parsing error at the time of writing at some point one can pass the entire dict instead
        self.capture_config = self.camera.create_still_configuration(raw={'size':self.sensor_modes[-1]['size'], 'format':self.sensor_modes[-1]['format']})
        # Set ctrl settings
        self.set_up_camera()

    def set_up_camera(self):
        """Set settings"""
        if self.config['Exposure'] != 'Auto':
            self.ctrl['ExposureTime'] = int(float(self.config['Exposure'])*1e6)
        else: 
            # Auto exposure wouldnt work proper so manually computing later
            self.auto_exp = True
            #self.ctrl['AeEnable'] = True
        # Configure sensor mode etc
        self.camera.configure(self.capture_config)
        # Set other settings
        self.camera.set_controls(self.ctrl)
        return


    def capture_image_and_download(self,name=None,check_max_tresh=None, pass_meta=None):
        """
        Starting and stopping camera occurs within this block to save on resouces
        As images wont be taken frequently

        check_max_tresh -> threshold for percentage of pixels at max val -> if cond satisfied returns true

        pass_meta --> extra meta to be passed to function
        """
        self.camera.start()

        time.sleep(3)
        
        if self.auto_exp:
            while True:
                request = self.camera.capture_request()
                # Request make array does not return bit depth image but pillow so uint8
                img=request.make_array('raw')
                exp = request.get_metadata()["ExposureTime"]
                new_exp = self.determine_exp(image=img, 
                                        img_exp_time=exp)
                if new_exp == True:
                    # Break loop if exposure good
                    break
                request.release()

                # Otherwise change and continue
                self.ctrl['ExposureTime'] = new_exp
                self.set_controls()
                    
        else:
            request = self.camera.capture_request()
        # Save last request made, for auto_exp it will have the correct exposure
        if name is None:
            im_name = "{}.dng".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        else:
            im_name = name
        if check_max_tresh is not None:
            img=request.make_array('raw')
        
        # Append dict to json metadata file, note that this method utilizes two opens to avoid loading it and still make json work
        # Also if it doesnt exist we dump a dictionary

        if not os.path.isfile('metadata.json'):
            with open('metadata.json', 'w') as convert_file:
                convert_file.write(json.dumps([]))        
        
        with open('metadata.json', 'ab') as convert_file:
            # Seek 1 offset from the end of the file
            convert_file.seek(-1, 2)
            # Converts to nr of bytes until current file location, should be most efficient method as it only changes its memory end adress
            convert_file.truncate()

        with open('metadata.json', 'a') as convert_file:
            dicti = request.get_metadata()
            dicti['Image_file_name'] = os.path.join(im_name)
            if pass_meta is not None:
                for i in pass_meta:
                    dicti[i] = pass_meta[i]
            # Add comma and newline so file can be read easier (i.e. if one wants to write own function remove first and last char of file just split \n remove the last char per line and json laods each line)
            convert_file.write(',\n')
            # Dump object
            convert_file.write(json.dumps(dicti))
            # Close list
            convert_file.write(']')

        request.save_dng(im_name)
        request.release()
        if hasattr(self.config, 'hdr'):
            if self.config['hdr']=='True':
                exp = request.get_metadata()["ExposureTime"]
                for i in [0.5,0.8,0.9,1.1,1.2,1.5]:
                    self.ctrl['ExposureTime'] = int(i*exp)
                    self.set_controls()
                    request = self.camera.capture_request()
                    im_name = "{}.dng".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
                    if name != None: 
                        im_name = name.split('.')[0]+'_{}.dng'.format(i)
                    request.save_dng(im_name)
                    request.release()
        # Stop camera and wait for next
        self.camera.stop()
        if check_max_tresh is not None:
            if np.sum(img==255)/img.size >= check_max_tresh:
                return True
            else:
                return None
        else:
            return None


    def set_controls(self,wait=True):
        """
        Helper fuction as exp and gain must be int and i forget to often
        Also fixes lower limit of exposure (absolute minimum cant be set)
        """
        self.ctrl['AnalogueGain'] = int(self.ctrl['AnalogueGain'])
        self.ctrl['ExposureTime'] = int(self.ctrl['ExposureTime'])
        if self.ctrl['ExposureTime'] == self.exp_limits[0]:
            # Minimum can not be set
            self.ctrl['ExposureTime'] = int(self.ctrl['ExposureTime']+5)
        self.camera.set_controls(self.ctrl)
        # Wait so that camera board can set new values (add a counterr in case it starts bugging out)
        counter = 0
        print('Waiting for camera board to recognize control changes')
        while wait:
            counter +=1
            metadata = self.camera.capture_metadata()
            if int(self.ctrl['ExposureTime'])*0.9<int(metadata["ExposureTime"])<int(self.ctrl['ExposureTime'])*1.1 and int(metadata["AnalogueGain"])==int(self.ctrl['AnalogueGain']) or counter >= 10:
                break
            else:
                time.sleep(0.1)
        return

    def determine_exp(self, image, img_exp_time, min_of_max=0.7, max_val = 0.8, img_bounds=None):
        '''Function to determine appropriate exposure from previous image -> based on max val
        All parameters are given relative to maximum acceptable value
        img_bounds is for interest in specfic areas

        returns True if condition satisfied so that min_of_max < max(img) < max_val

        '''
        # So the image is a np.uint8 array of double width, 
        # by callin np.uint16 it combines each two items into 1 element
        # This needs to be done as there are no non power two uint datatypes so we convert to uint16 to combine them
        # Our max datatype corresponds to bit depth not to the datatype
        # Here is the thread where i learned https://github.com/raspberrypi/picamera2/issues/736
        img = img.view(np.uint16)
        if 'IMG_Bounds' in self.config:
            bounds = [int(i) for i in self.config['IMG_Bounds'].split(',')]
            image = image.astype(np.float64)[bounds[0]:bounds[2], bounds[1]:bounds[3]]
        else:
            # Now we convert to float so taht we can do math
            image = image.astype(np.float64)
        print('Old exposure ', img_exp_time) 
        dtype_max = 2**self.bit_depth - 1
        max_val *= dtype_max
        min_of_max *= dtype_max
        print('Want {} < {} < {}'.format(min_of_max, np.max(image), max_val))
        if min_of_max < np.max(image) < max_val:
            return True
        else:
            # Compute new time -> attempt to get midpoint of max and min of max
            # TODO: Add polynomial calibration for exposure time per iso for linearity
            new  = int(img_exp_time * (min_of_max+max_val)/(2*np.max(image)))
            print('Computed exp: {}'.format(new))
            # In case exp limits is reached
            if self.ctrl['AnalogueGain'] > 1 and new < 0.7*self.ctrl['ExposureTime']:
                # Decreasing Gain and increasing exposure time
                self.ctrl['AnalogueGain'] -= 1
                self.ctrl['ExposureTime'] = self.exp_limits[1]

            if new>self.exp_limits[1]:
                print('Setting maximum exposure value {}'.format(self.exp_limits[1]))
                new = self.exp_limits[1] 
            # In case exp limit was already reached (Exp limit is never set always about 15 ms shorter)
            if img_exp_time >= self.exp_limits[1]*0.95:
                print('Increasing AnalogueGain as exp limit is reached')
                self.ctrl['AnalogueGain'] = int(self.ctrl['AnalogueGain']+1)
                new = int(self.exp_limits[1]/2)
            return new
        
    def take_bias(self, num_im=50, Gain=1):
        """Helper function to take bias frames
        num_im -> number of images to be taken
        ISO -> ISO at which to take -> list is acceptable and will iterate over
        """
        self.auto_exp = False
        self.config['HDR'] = 'False'
        bias_path = os.path.join(os.environ['HOME'], 'Bias')
        os.mkdir(bias_path)
        multip_iso = False
        if type(Gain) in [np.ndarray, list]:
            if len(Gain)>1:
                multip_iso = True
        self.ctrl['ExposureTime'] = self.exp_limits[0]+20 # Zero division in source code in changing to shutter
        if not multip_iso: Gain = [Gain]
        for i in Gain:
            self.ctrl['AnalogueGain'] = i
            # Generate subdirectories for each ISO if more than one
            if multip_iso: 
                path = os.path.join(bias_path, str(i))
                os.mkdir(path)
            else: path = bias_path
            self.set_controls(wait=False)
            for j in range(num_im):
                self.capture_image_and_download()
        self.camera.stop()
        return 
    
    def take_darks(self, num_im, exp, gain):
        """
        Not yet sure how to handle temperature changes from imaging
        for now just take images and see how it changes as a function of time
        """
        self.auto_exp = False
        self.config['HDR'] = 'False'
        dark_path = os.path.join(os.environ['HOME'], 'Darks')
        os.mkdir(dark_path)
        multip_iso = False
        multip_exp = False
        if type(gain) in [np.ndarray, list]: 
            if len(gain)>1: multip_iso = True
        if type(exp) in [np.ndarray, list]: 
            if len(gain)>1: multip_exp = True
        for i in exp:
            self.ctrl['ExposureTime'] = i
            if multip_exp: 
                exp_path = os.path.join(dark_path, str(i))
                os.mkdir(path)
            else: exp_path = dark_path
            for j in gain:
                self.ctrl['AnalogueGain'] = j
                if multip_iso: 
                    path = os.path.join(exp_path, str(j))
                    os.mkdir(path)
                else: path = exp_path
                os.chdir(path)
                self.set_controls(wait=False)
                for k in range(num_im):
                    self.capture_image_and_download()   
                time.sleep(30)
        return

    def take_linearity(self, num_im_exp_sweep=10,num_im_gain_sweep=20,num_im=2):
        """Sweeps each combination between min max in provided steps, stops when half the image values are at a maximum
        num_im refers to images per stop
        put it in some differently lit environments
        """
        self.ctrl['ExposureTime'] = self.exp_limits[0]+5
        self.ctrl['AnalogueGain'] = self.gain_limts[0]

        self.auto_exp = False
        self.config['HDR'] = 'False'

        exp_range = np.linspace(self.exp_limits[0], self.exp_limits[1], num_im_exp_sweep)
        gain_range = np.linspace(self.gain_limts[0], self.gain_limts[1], num_im_gain_sweep)
        linearity_path = os.path.join(os.environ['HOME'], 'Linearity')
        os.mkdir(linearity_path)
        os.chdir(linearity_path)
        for i in exp_range:
            self.ctrl['ExposureTime'] = i
            for j in gain_range:
                self.ctrl['AnalogueGain'] = j
                self.set_controls(wait=False)
                for k in range(num_im):
                    res = self.capture_image_and_download(name='{}_{}.dng'.format(i,j),check_max_tresh=0.3)
                    if res:
                        # If threshhold max value reached break inner loop
                        break
        return






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
            if not DEBUG:
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
            
        if 'MotorAzi' in config:
            self.MotorAzi = config["MotorAzi"]

        
        # Extract file paths
        self.paths = config["Paths"]

        self.location = config['Location']
        
        pass

    def load_config(self,path):
        config = cfg.ConfigParser()
        config.read(path)
        return config




class MotorController_ULN2003:
    """For moving camera set ups controls 1 motor
    default set up for 28BYJ-48 motor (come really cheap as set)
    """
    step_sequence = [[1,0,0,1],
                 [1,0,0,0],
                 [1,1,0,0],
                 [0,1,0,0],
                 [0,1,1,0],
                 [0,0,1,0],
                 [0,0,1,1],
                 [0,0,0,1]]
    # Variable below keeps track of current index in list
    stp_counter = 0
    deg_per_step = 5.625*1/64 
    # Variable to track total angle traveled during operation
    total_angle = 0 
    # Direction 
    dir = True
    def __init__(self, gpio, delay = 0.01, name='azi') -> None:
        """
        NEVER: Step over or under 360 degrees relative to total_move --> it will most likely mess up the cabling
        gpio --> list of ms1 to ms4 in order in BCM listing (name of pins not pin number)
        delay --> delay between each step
        name --> name to be used to save current rotation state to assure it doesnt break itself
        """
        gpio = [int(i) for i in gpio]
        self.ms = gpio
        self.delay = delay
        self.name = name
        GPIO.setmode( GPIO.BCM )
        for i in gpio:
            GPIO.setup(i,GPIO.OUT)
            GPIO.output(i,GPIO.LOW)
        # Read past state
        if os.path.isfile(os.path.join('/home', self.name+'.curr_rot')):
            with open(os.path.join('/home', self.name+'.curr_rot'),'r') as f:
                cont = f.read()
                # In case the file was manually created
                if len(cont) != 0:
                    self.total_angle = float(cont)
                else:
                    pass
        # We attempt to write to the file to check it has the right permissions, this will result in error if it doesnt
        try:
            with open(os.path.join('/home', self.name+'.curr_rot'),'w') as f:
                f.write(str(self.total_angle))
        except Exception as e:
            print(e)
            print('The curr rotation value file has the wrong permissions! Fix it (chmod a+rwx fpath) then restart')
            sys.exit(0)

        pass

    def move_to_angle(self,angle):
        """Helper function move to"""
        move = angle-self.total_angle
        # Negative move corresponds to dir = False
        if move < 0 and self.dir: 
            self.change_dir()
        elif move> 0 and not self.dir:
            self.change_dir()
        elif move == 0:
            return self.total_angle
        move = abs(move)
        print('Absolute angle to move: ', move)
        self.step_angle(move)
        return self.total_angle

    def change_dir(self):
        self.dir = not self.dir
        return

    def step_angle(self,angle):
        """
        Steps just under the angle specified, 
        returns actual angle stepped
        """
        steps = angle//self.deg_per_step
        self.step(step_count=int(steps))
        
        return steps*self.deg_per_step

    
    def step(self,step_count):
        """Take step count number steps"""
        i = 0
        for i in range(step_count):
            for pin in range(0, len(self.ms)):
                GPIO.output( self.ms[pin], self.step_sequence[self.stp_counter][pin] )
            if self.dir==True:
                self.stp_counter = (self.stp_counter - 1) % 8
            elif self.dir==False:
                self.stp_counter = (self.stp_counter + 1) % 8
            time.sleep( self.delay )
        if self.dir:
            self.total_angle +=step_count*self.deg_per_step
        else:
            self.total_angle -= step_count*self.deg_per_step

        with open(os.path.join('/home', self.name+'.curr_rot'),'w') as f:
            f.write(str(self.total_angle))
        return 


if __name__=='__main__':
    main()