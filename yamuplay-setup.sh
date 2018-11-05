#!/bin/bash
scriptdir=`pwd`

# Download external libraries from https://github.com if they don't exist:
if [ ! -d pyudev ]; then
    git clone https://github.com/pyudev/pyudev.git
else
    echo "Directory ./pyudev already exists"
fi
if [ ! -d python-omxplayer-wrapper ]; then
    git clone https://github.com/willprice/python-omxplayer-wrapper.git
else
    echo "Directory ./python-omxplayer-wrapper already exists"
fi
if [ ! -d python-magic ]; then
    git clone https://github.com/ahupp/python-magic.git
else
    echo "Directory ./python-magic already exists"
fi
# Install external libraries:
# python3-dbus v1.2.4-1
sudo apt-get -y install python3-dbus
# pyudev v0.21.0.dev20181104
cd pyudev
sudo python3 setup.py install
cd ..
# python-omxplayer-wrapper v0.3.1
cd python-omxplayer-wrapper
sudo python3 setup.py install
sudo python3 -m pip install mock
cd ..
# python-magic v0.4.16
cd python-magic
sudo python3 setup.py install
cd ..

# create desktop icon and start menu item:
echo [Desktop Entry] > yamuplay.desktop
echo Version=0.4.0 >> yamuplay.desktop
echo Name=yamuplay >> yamuplay.desktop
echo Comment=Yet Another MUsic PLAYer based on omxplayer >> yamuplay.desktop
echo Path=$scriptdir >> yamuplay.desktop
echo TryExec=$scriptdir/yamuplay.py >> yamuplay.desktop
echo Exec=$scriptdir/yamuplay.py -o alsa -k 1 >> yamuplay.desktop
echo Icon=$scriptdir/yamuplay.png >> yamuplay.desktop
echo Terminal=false >> yamuplay.desktop
echo Type=Application >> yamuplay.desktop
echo Categories=AudioVideo\; >> yamuplay.desktop
echo StartupNotify=true >> yamuplay.desktop
# desktop icon:
cd ~/Desktop
if [ -h yamuplay.desktop ]; then
    rm yamuplay.desktop
fi
ln -s $scriptdir/yamuplay.desktop
# start menu item:
cd /usr/share/applications
if [ -h yamuplay.desktop ]; then
    sudo rm yamuplay.desktop
fi
sudo ln -s $scriptdir/yamuplay.desktop
