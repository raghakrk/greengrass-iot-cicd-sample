#!/bin/bash
make all
zip deploy_package.zip hello
make clean
aws s3 mv deploy_package.zip s3://iot-gg-cicd-sample
