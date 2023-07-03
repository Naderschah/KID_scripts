#!/usr/bin/python

"""
All methods I found for automatically launching applications on a raspberry are flakey or jsut dont work for me.
So this is supposed to be a script run by cron to check if a script is running and then start it 
"""
import subprocess
import psutil
import datetime
import sys

for process in psutil.process_iter():
    counter = 0
    while True:
        if 'gphoto' in process.cmdline():
            # Wait 30 sec for camera to finish
            time.sleep(30)
            counter+=1
        else:
            out = len(subprocess.check_output('gphoto2 --auto-detect').split(b'\n'))
            if out < 4:
                with open(os.path.join('/tmp', 'CAMERA_GONE')):
                    f.write(' ')
                with open(os.path.join(so.environ['HOME'], 'CAMERA_DEAD.log')):
                    f.write(datetime.now().strftime('%Y%m%d-%H%M%S'))
        if counter == 3:
            sys.exit(0)