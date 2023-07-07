#!/bin/bash
# Make sure when creating this archive on the raspberries to run chmod a+rwx -R on it so we dont worry about permissions
rasp_path=/home/Archive
server_path=/net/vega/data/users/observatory/SkyCams/

raspberies=(EOSRP@192.168.1.144 spectroscope@192.168.1.137)

for  i in ${!raspberies[@]}; do
        echo ${raspberies[$i]};
        rsync -arzP --remove-source-files --ignore-existing -e "ssh" ${raspberies[$i]}:$rasp_path $server_path 
done