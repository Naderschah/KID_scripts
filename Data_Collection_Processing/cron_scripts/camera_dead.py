#!/usr/bin/python

"""
All methods I found for automatically launching applications on a raspberry are flakey or jsut dont work for me.
So this is supposed to be a script run by cron to check if a script is running and then start it 
"""
import subprocess
import psutil
import datetime
import sys
import time
import os
import telegram

# Tele bot token and chat_id (to be placed in .bashrc)
token = os.environ['TOKEN']
chat_id = os.environ['CHAT_ID']

for process in psutil.process_iter():
    counter = 0
    while True:
        if any(['gphoto' in i for i in process.cmdline()]):
            # Wait 30 sec for camera to finish
            time.sleep(30)
            counter+=1
        else:
            out = len(subprocess.check_output('gphoto2 --auto-detect').split(b'\n'))
            if out < 4:
                # Make file that can be read from other machines
                with open(os.path.join('/tmp', 'CAMERA_GONE')) as f:
                    f.write(' ')
                # Log time in case we ever do debugging
                with open(os.path.join(os.environ['HOME'], 'CAMERA_DEAD.log')):
                    f.write(datetime.now().strftime('%Y%m%d-%H%M%S'))
                # Send message over telegram bot
                bot = telegram.Bot(token)
                async with bot:
                    try: # In case hostname is not specific enough this environemnt variable can be set (in bashrc remember they are not persistent)
                        name = os.environ['DESCRIPTOR']
                    except:
                        name = os.environ['HOSTNAME']
                    await bot.send_message(text='Camera of Device {} is down'.format(name), chat_id=chat_id)
        # Timer in case it gets stuck somewhere
        if counter == 3:
            sys.exit(0)