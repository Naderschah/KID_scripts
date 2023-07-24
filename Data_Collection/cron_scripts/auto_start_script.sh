#!/bin/bash
# Add Home Path !!
HOME=/home/EOSRP/

# Added into cronjob as 
# 30 * * * * /home/EOSRP/auto_start_script.sh
# Make sure to have this executable
script_name=allsky-v7.0.py

process_counts=$(ps aux | grep -i 'python' | grep -i $script_name | wc -l)

# 0 is true 1 is false
if [ $process_counts -eq 0 ]
then
    # Piping doesnt create files
    if [ ! -e ${HOME}Imaging_Output.txt ] ; then
        touch ${HOME}Imaging_Output.txt
    fi
    echo "Start Script"
    /usr/bin/python $HOME$script_name >>  ${HOME}Imaging_Output.txt
else
    echo "Script running"
fi
