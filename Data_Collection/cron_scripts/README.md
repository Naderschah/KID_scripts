## Cron Scripts

These scripts are aimed at automating the raspberries and working around the fact that we cant  make major modifications to the germans scripts. Quick note on cron, it expects 1 argument commands so 1 path nothing more, to avoid this one can write a bash script that does the two or whatever many commands or wrap it like so:  bash "execute func"  allthough I dont recall how well the latter worked

- auto_start_script.sh : To be entered into the crontab and run every 30 minutes, as all methods I found for autostarting the script on boot were somewhat irregular, this script checks if script of scriptname is running (if the name changes, change it in there too) and if not starts it while redirecting the output to Imaging_Output, not really useful for debugging, unless the print statements I added remain in the script (and then even it remains hard)

- camera_dead.py : Im not sure this script actually worked, the issue arrises from evironment variables, cron doesnt seem to have access to all, it may have been fixed by executing it with bash and sourcing the environment variables, but these may require explicit assignment, point of this script is to send a message with a telegram bot when the camera fails, this is only useful if one needs to manually restart the cameras (say with the 5g brick the germans have) or if one is doing debugging, if the timer bricks remain in use it shouldnt matter.

- file_management.sh : The script run on serverside to copy the raspberries data, it was modified to work through a jumphost (ssh jumphost inside the quotation before the current ssh in the rsync command), for remote networks the same structure will work but a second block may need to be added depending on the server structure.


