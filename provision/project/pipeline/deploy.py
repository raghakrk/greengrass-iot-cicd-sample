"""
Deployment script for greengrass
"""
import json
import argparse
import os
from pathlib import Path
import boto3

Path("out").mkdir(parents=True, exist_ok=True)
FAILURES_FILE = os.environ.get('FAILURES_FILE','out/deployment_failures.json')
PARAMETER_FILE = 'deploy_params.json'

client = boto3.client('greengrassv2')

def create_new_deployment(deployment_config, target_arn, deployment_name):
    "Create new Deployment or revise existing deployment"
    if deployment_config:
        response = client.create_deployment(**deployment_config)
    else:
        response = client.create_deployment(
            targetArn=target_arn,
            deploymentName=deployment_name,
            components={
                'HelloWorld-example-cpp': {
                    'componentVersion': '1.0.2'
                },
                'aws.greengrass.ShadowManager':{
                    'componentVersion': '2.0.2'
                }
            }
        )
    return response

def create_deploy_params(target_arn, deployment_name):
    "create deployment parameters"
    response = client.list_deployments(
        targetArn=target_arn,
        historyFilter='LATEST_ONLY',
        maxResults=100,
    )
    existing_deployment = False
    deployment_id=""
    deployment_config={}
    for deployment in response["deployments"]:
        if deployment["deploymentName"] == deployment_name:
            deployment_id = deployment["deploymentId"]
            existing_deployment = True
            break
    if existing_deployment:
        deployment_config = client.get_deployment(deploymentId=deployment_id)
        keys_to_remove = ["deploymentId", "revisionId", "iotJobId", "iotJobArn",
            "creationTimestamp", "isLatestForTarget", "deploymentStatus", "ResponseMetadata"]
        try:
            for key in keys_to_remove:
                deployment_config.pop(key)
            if not deployment_config["tags"]:
                deployment_config.pop("tags")
        except KeyError:
            pass
    return deployment_config

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='greengrass v2 deployment script')
    parser.add_argument('--target-arn',
        default="arn:aws:iot:us-west-2:465906353389:thinggroup/main")
    parser.add_argument('--deployment-name', default="iot-gg-main")
    args = parser.parse_args()
    target_arn_ = args.target_arn
    deployment_name_ = args.deployment_name
    deployment_config_params = create_deploy_params(target_arn_, deployment_name_)
    deployment_config_params['components']["aws.greengrass.ShadowManager"] = {
        'componentVersion': '2.0.2'
    }
    deployment_response = create_new_deployment(deployment_config_params,
        target_arn_, deployment_name_)
    deploy_params = client.get_deployment(
        deploymentId=deployment_response["deploymentId"]
    )
    deploy_params.pop("ResponseMetadata")
    print(deploy_params)
    f = open(PARAMETER_FILE, "w+")
    f.write(json.dumps(deploy_params, indent=4, sort_keys=True, default=str))
    f.close()
    core_device_list = client.list_core_devices(
        thingGroupArn=target_arn_
    )
    done_deployments = []
    failed = []
    for core_device in core_device_list["coreDevices"]:
        status = core_device["status"]
        if status == 'HEALTHY':
            done_deployments.append(core_device['coreDeviceThingName'])
        else:
            failed.append(core_device['coreDeviceThingName'])
    f = open(FAILURES_FILE, "w+")
    f.write(json.dumps(failed))
    f.close()
    if len(failed) != 0:
        raise Exception("Unable to complete deployment: {}".format(failed))
