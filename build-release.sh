#!/bin/bash
aws configure import --csv file:///home/automotus/accessKeys.csv
cd /home/automotus/optix/
sudo make all
zip deploy_package.zip hello
sudo make clean
sudo aws s3 mv deploy_package.zip s3://iot-gg-cicd-sample --region us-west-2
