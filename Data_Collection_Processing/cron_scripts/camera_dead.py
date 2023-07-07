#!/usr/bin/python

"""
For KID groningen no longer required, our devices turn off every day through a time switch on the powerbrick, set to somewhere around 3pm 

Copy this script to ~

To automatically send a message to telegram when camera dies
file:
.cam_dead_rc
needs to be created, cron source bashrc doesnt work as its set to return in line 5-10 somewhere, with the environment variables:
TOKEN :: Token of chat bot
CHAT_ID :: Chat ID of chat bot activity (url extension in telegram web without the #-)
HOSTNAME :: (or DESCRIPTOR) Name to show up in telegram
HOME :: the same as the HOME environment variable pointing to ~ (cd ~; pwd : output will be home)
In cron:

# m h  dom mon dow   command
0 * * * * bash -c "source $HOME/.cam_dead_rc; /usr/bin/python3 /home/EOSRP/camera_dead.py"

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