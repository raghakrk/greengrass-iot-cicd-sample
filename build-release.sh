#!/bin/bash
cd /home/nano/optix/
sudo make all
zip deploy_package.zip hello
sudo make clean
