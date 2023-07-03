#!/usr/bin/python

"""
All methods I found for automatically launching applications on a raspberry are flakey or jsut dont work for me.
So this is supposed to be a script run by cron to check if a script is running and then start it 

In cron:
# Edit this file to introduce tasks to be run by cron.
# 
# Each task to run has to be defined through a single line
# indicating with different fields when the task will be run
# and what command to run for the task
# 
# To define the time you can provide concrete values for
# minute (m), hour (h), day of month (dom), month (mon),
# and day of week (dow) or use '*' in these fields (for 'any').
# 
# Notice that tasks will be started based on the cron's system
# daemon's notion of time and timezones.
# 
# Output of the crontab jobs (including errors) is sent through
# email to the user the crontab file belongs to (unless redirected).
# 
# For example, you can run a backup of all your user accounts
# at 5 a.m every week with:
# 0 5 * * 1 tar -zcf /var/backups/home.tgz /home/
# 
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command
0 * * * * source $HOME/.bashrc; /usr/bin/python3 /home/EOSRP/camera_dead.py
30 * * * * source $HOME/.bashrc; /usr/bin/python3 /home/EOSRP/auto_start_script.py

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
with open(os.path.join(os.environ['HOME'], 'script_off.txt'), 'a') as f:
    f.write(datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
# Execute new child thread
Popen(['/usr/bin/python',os.path.join(os.environ['HOME'],script_name), '>>', os.path.join(os.environ['HOME'], 'Imaging_Output.txt')])