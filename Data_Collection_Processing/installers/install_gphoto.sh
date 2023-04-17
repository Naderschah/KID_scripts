#!/bin/bash
apt update # Basic install requirements - Takes quite some time
apt upgrade 
apt install -y git gphoto2 vim tmux # Basic utility requirement (tmux for persistent session over ssh)
