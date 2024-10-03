#!/bin/bash

# Build april tag tracker
cd April-Tag-VR-FullBody-Tracker
mkdir build
cd build
cmake ..
make

cd ../../
mkdir build

# Make dummy driver folder
cd build
mkdir apriltagtrackers
cd apriltagtrackers
cp ../../driver.vrdrivermanifest .
cp -r ../../resources .
mkdir -p bin/linux64
cp ../../April-Tag-VR-FullBody-Tracker/build/BridgeDriver/driver_apriltagtrackers.so bin/linux64

cd ..

# Copy install and uninstall scripts
cp ../April-Tag-VR-FullBody-Tracker/BridgeDriver/install_driver.sh .
cp ../April-Tag-VR-FullBody-Tracker/BridgeDriver/uninstall_driver.sh .
