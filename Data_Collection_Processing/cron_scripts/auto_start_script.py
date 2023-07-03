#!/usr/bin/python

"""
All methods I found for automatically launching applications on a raspberry are flakey or jsut dont work for me.
So this is supposed to be a script run by cron to check if a script is running and then start it 
"""
script_name = 'allsky-v7.0.py'
import psutil
import sys
from subprocess import Popen
import datetime
import os

for process in psutil.process_iter():
    if process.cmdline() == ['python', script_name]:
         sys.exit('Process found: exiting.')
# Make note when script was noticed to be off (in case we want to make running diagnostics)
with open(os.path.join(os.environ['HOME'], 'script_off.txt'), 'a') as f:
    f.write(datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
Popen(['python', 'update.py'])