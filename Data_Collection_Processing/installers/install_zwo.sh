apt update 
apt upgrade 
apt install -y git wget tar
wget -O ZWO-SDK.tar.bz2 "https://dl.zwoastro.com/software?app=AsiCameraDriverSdk&platform=macIntel&region=Overseas"
tar -xvjf ZWO-SDK.tar.bz2
echo "Finish this"