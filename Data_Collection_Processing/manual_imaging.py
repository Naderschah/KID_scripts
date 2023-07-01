"""
This script is intended for taking calibration images when no wifi/monitor is available
Using the instructions below to set it up on boot one can use two leds for status indication (one is sufficient)
and a button all connected to the gpio ports to take an image
IMPORTANT: Place the correct resistor between led and ground so that gpio doesnt burn out

The code used is based on the Data collection class for the picamera
"""

gpio_led_red_anode = 2
gpio_led_green_anode = 14
gpio_button_sig_out = 15
gpio_button_sig_in  = 18

import sys
import RPi.GPIO as GPIO
from data_collection import *

CODE_DIR = os.path.abspath(os.getcwd())
# Code Dir and File dir mustnt overlap
FILE_DIR = os.path.abspath(__file__)
FILE_PARENT = '/'+'/'.join(FILE_DIR.split('/')[:-1:])+'/'





def main():
    # GPIO Set up - pin names 
    GPIO.setmode(GPIO.BCM)
    # Set out in and initial state 
    GPIO.setup(gpio_led_red_anode, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(gpio_led_green_anode, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(gpio_button_sig_out, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(gpio_button_sig_in, GPIO.IN)

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

    # Sets up folder for night and switches directory
    file_handler = File_Handler(config.paths)
    # Set up camera control - each init will check the correct camera and brand is 
    if config.camera['Brand'] in ["Canon", "Nikon"]: # Add the other ones if required
        camera = Camera_Handler_gphoto(config)
    elif config.camera['Brand'] == "ZWO": 
        camera = Camera_Hanlder_ZWO(config)
    elif config.camera['Brand'] == "PiCamera": 
        camera = Camera_Handler_picamera(config)


    # Wait for button press
    while True:
        # We are now ready so disable red enable green
        GPIO.output(gpio_led_green_anode, GPIO.HIGH)
        GPIO.output(gpio_led_red_anode, GPIO.LOW)
        # The below waits until button press (rising edge -> Low to high)
        channel = GPIO.wait_for_edge(gpio_button_sig_in, GPIO.RISING)

        # Set imaging indicator
        GPIO.output(gpio_led_green_anode, GPIO.LOW)
        GPIO.output(gpio_led_red_anode, GPIO.HIGH)

        camera.capture_image_and_download()

    # The below is for cameras that require closing at the end of the night
    camera.finish()
    
    GPIO.cleanup()



if __name__=='_main__':
    try:
        main()
    except:
        # To show exception occured
        GPIO.output(gpio_led_green_anode, GPIO.LOW)
        GPIO.output(gpio_led_red_anode, GPIO.HIGH)
        time.sleep(5)
        GPIO.cleanup()
        sys.exit(1)

