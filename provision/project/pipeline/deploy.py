"""
Deployment script for greengrass
"""
import json
import argparse
import os
from pathlib import Path
import boto3
import logging
from pathlib import Path
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)   

Path("out").mkdir(parents=True, exist_ok=True)
FAILURES_FILE = os.environ.get('FAILURES_FILE','out/deployment_failures.json')
DEPLOYMENT_STATUS_FILE = 'deployment_status.json'
PARAMETER_FILE = 'deploy_params.json'
client = boto3.client('greengrassv2')

def check_component_version_exist(component_name, component_version):
    response = client.list_components()
    component_exist = False
    for component in response["components"]:
        if component_name == component["componentName"]:
            component_arn = component["latestVersion"]["arn"]
            response_version = client.list_component_versions(
                arn=component_arn
            )
            for component_version_iter in response_version['componentVersions']:
                if component_version_iter["componentVersion"] == component_version:
                    component_exist=True
                    break
            break
    return component_exist

def create_custom_component(component_params):
    recipe_path = component_params["componentRecipePath"]
    component_tags = component_params["tags"]

    recipe = read_json(recipe_path)
    response = client.create_component_version(
        inlineRecipe=json.dumps(recipe, indent=2).encode('utf-8'),
        tags=component_tags
    )
    status = response["status"]
    if status["errors"]:
        raise Exception('failed to create component \n{}'.format(status["errors"])) 
    logger.info(status["message"])

def check_deployment_status(target_arn, deployment_name):
    
    response = client.list_deployments(
        targetArn=target_arn,
        historyFilter='LATEST_ONLY',
        maxResults=100,
    )
    existing_deployment = False if len(response["deployments"]) == 0 else True
    deployment_id = None
    if existing_deployment:
        deployment_id = response["deployments"][0]["deploymentId"]
    return existing_deployment, deployment_id

def create_deployment(deployment_config):
    response = client.create_deployment(**deployment_config)
    return response


def generate_deploy_params(existing_deployment, deployment_params, deployment_group, deployment_id=None):
    deployment_config={}
    if existing_deployment:
        deployment_config = client.get_deployment(deploymentId=deployment_id)
        keys_to_remove = ["deploymentId", "revisionId", "iotJobId", "iotJobArn",
            "creationTimestamp", "isLatestForTarget", "deploymentStatus", "ResponseMetadata"]
        default_components=['aws.greengrass.Cli', 'aws.greengrass.Nucleus']
        # delete all keys which are not neccesary for deployment revision
        try:
            for key in keys_to_remove:
                deployment_config.pop(key)
            if not deployment_config["tags"]:
                deployment_config.pop("tags")
        except KeyError:
            pass
        # delete all components except default ones
        temp_component_dict = {}
        for component, component_info in deployment_config['components'].items():
            if component in default_components:
                temp_component_dict.update({component: component_info})
        deployment_config['components'] = temp_component_dict
        # add Public components
        for public_component in deployment_params["publicComponents"]:
            deployment_config['components'].update(public_component)
        # add custom component
        for custom_component in deployment_params["customComponents"]:
            component_name = custom_component["componentName"]
            component_version = custom_component["componentVersion"]
            # check whether component exist. If not, create a new component
            if not check_component_version_exist(component_name, component_version):
                create_custom_component(custom_component)
            # append component configuration to the deployment_config file
            deployment_config['components'].update(
                {
                    component_name: {
                        "componentVersion":component_version
                    }
                }
            )
    else:
        target_arn=deployment_params[deployment_group]["targetArn"]
        deployment_name=deployment_params[deployment_group]["deploymentName"]
        components ={}
        # add Public components
        for public_component in deployment_params["publicComponents"]:
            components.update(public_component)
        # add custom component
        for custom_component in deployment_params["customComponents"]:
            component_name = custom_component["componentName"]
            component_version = custom_component["componentVersion"]
            # check whether component exist. If not, create a new component
            if not check_component_version_exist(component_name, component_version):
                create_custom_component(custom_component)
            # append component configuration to the deployment_config file
            components.update(
                {
                    component_name: {
                        "componentVersion":component_version
                    }
                }
            )
        deployment_config.update(
            {
                "targetArn":target_arn,
                "deploymentName":deployment_name,
                "components":components
            }
        )
    return deployment_config

def read_json(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError("file {} does not exist".format(filepath))
    f = open(filepath,)
    data = json.load(f)
    f.close()
    return data

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='greengrass v2 deployment script')
    parser.add_argument('--target-name', default="canary")
    args = parser.parse_args()
    target_name = args.target_name
    deployment_params = read_json(PARAMETER_FILE)
    if target_name == "main":
        deployment_group = "mainDeploymentParams"
    else:
        deployment_group = "canaryDeploymentParams"

    target_arn = deployment_params[deployment_group]["targetArn"]
    deployment_name = deployment_params[deployment_group]["deploymentName"]

    existing_deployment, deployment_id = check_deployment_status(target_arn, deployment_name)
    
    deployment_config = generate_deploy_params(existing_deployment, deployment_params, deployment_group, deployment_id)

    deployment_response = create_deployment(deployment_config)

    deployment_status = client.get_deployment(
        deploymentId=deployment_response["deploymentId"]
    )

    done_deployments = []
    failed = []
    for i in range(100):
        core_device_list = client.list_core_devices(
            thingGroupArn=target_arn
        )
        deployments = core_device_list["coreDevices"]
        for deployment in done_deployments:
            deployments.remove(deployment)
        for core_device in deployments:
            status = core_device["status"]
            coreDeviceThingName = core_device["coreDeviceThingName"]
            print('coreDeviceThingName {} Status: {}'.format(coreDeviceThingName,status))

            if status == 'HEALTHY':
                done_deployments.append(core_device)
                deployments.remove(core_device)
                if core_device in failed:
                    failed.remove(core_device)
            elif status == 'UNHEALTHY':
                failed.append(core_device)
       
        if len(deployments) == 0:
            break

        time.sleep(1.0)

    if len(failed) > 0:
        print('Deployment Failed: {}'.format(failed))

    if len(failed) == 0 and len(deployments) == 0:
        print('Deployment Success')

    if len(deployments) > 0:
        print('Deployment timed out')
        failed.append('TIMEOUT')

    f = open(FAILURES_FILE, "w+")
    f.write(json.dumps(failed))
    f.close()
