#!/bin/bash
cd /home/nano/optix/
ls
sudo make all
zip deploy_package.zip hello
sudo make clean
sudo aws s3 mv deploy_package.zip s3://iot-gg-cicd-sample
