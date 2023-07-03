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
import subprocess
import psutil
import datetime
import sys
import time
import os
import telegram
import asyncio
# Tele bot token and chat_id (to be placed in .bashrc)
token = os.environ['TOKEN']
chat_id = os.environ['CHAT_ID']

async def send_message():
    token = os.environ['TOKEN']
    chat_id = os.environ['CHAT_ID']
    bot = telegram.Bot(token)

    async with bot:
        try: # In case hostname is not specific enough this environemnt variable can be set (in bashrc remember they are not persistent)
            name = os.environ['DESCRIPTOR']
        except:
            name = os.environ['HOSTNAME']
        await bot.send_message(text='Camera of Device {} is down'.format(name), chat_id=chat_id)



for process in psutil.process_iter():
    counter = 0
    while True:
        if any(['gphoto' in i for i in process.cmdline()]):
            # Wait 30 sec for camera to finish
            time.sleep(30)
            counter+=1
        else:
            out = len(subprocess.check_output(['gphoto2','--auto-detect']).split(b'\n'))
            if out < 4:
                # Make file that can be read from other machines
                with open(os.path.join('/tmp', 'CAMERA_GONE'), 'a') as f:
                    f.write(' ')
                # Log time in case we ever do debugging
                with open(os.path.join(os.environ['HOME'], 'CAMERA_DEAD.log'), 'a') as f:
                    f.write(datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
                asyncio.run(send_message())
            sys.exit(0)
        # Timer in case it gets stuck somewhere
        if counter == 3:
            sys.exit(0)