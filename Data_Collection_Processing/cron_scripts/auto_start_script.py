#!/usr/bin/python
# Add Home Path !!
HOME = '/home/EOSRP/'

"""
Installs required:
sudo apt install python3-psutil
above doesnt seem to ship with python3 on arm

All methods I found for automatically launching applications on a raspberry are flakey or jsut dont work for me.
So this is supposed to be a script run by cron to check if a script is running and then start it if not

In cron:

# m h  dom mon dow   command
30 * * * * /usr/bin/python3 /home/EOSRP/auto_start_script.py

"""
script_name = 'allsky-v7.0.py'

import psutil
import sys
from subprocess import Popen
import datetime
import os

for process in psutil.process_iter():
    cmd = process.cmdline()
    # Check if keywords present
    if  any(['python' in i for i in cmd]) and any([script_name in i for i in cmd]):
         sys.exit('Process found: exiting.')
# Make note when script was noticed to be off (in case we want to make running diagnostics)
with open(os.path.join(HOME, 'script_off.txt'), 'a') as f:
    f.write(datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
# Execute new child thread
Popen(['/usr/bin/python',os.path.join(HOME,script_name), '>>', os.path.join(HOME, 'Imaging_Output.txt')])