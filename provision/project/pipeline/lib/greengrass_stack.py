# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import (
    core,
    aws_codecommit as codecommit,
    aws_codedeploy as code_deploy,
    aws_iam as iam,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
)
import os
import json
PARAMETER_FILE="./deploy_params.json"

if not os.path.exists(PARAMETER_FILE):
    raise FileNotFoundError("file {} does not exist".format(PARAMETER_FILE))


class GreengrassPipelineStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        f = open(PARAMETER_FILE,)
        deploy_params = json.load(f)
        f.close()

        repository_name = deploy_params['repositoryName']
        repository_branch = deploy_params['repositoryBranchName']
        on_premise_instance_tags = deploy_params['onPremiseInstanceTags']

        code = codecommit.Repository.from_repository_name(
            self, "CodeRepo", repository_name=repository_name
        )
        serverApplication = code_deploy.ServerApplication(
            self, "GreenGrassDeployment", application_name="GreenGrassDeployment",
        )

        # The code that defines your stack goes here
        code_deploy.ServerDeploymentGroup(
            self,
            "CodeDeploymentGroup",
            application=serverApplication,
            deployment_group_name="GreenGrassDeploymentGroup",
            deployment_config=code_deploy.ServerDeploymentConfig.ONE_AT_A_TIME,
            on_premise_instance_tags =code_deploy.InstanceTagSet(
                on_premise_instance_tags,
            ),
        )
        cdk_deploy_canary = codebuild.PipelineProject(
            self,
            "Deploy",
            project_name="canary",
            build_spec=codebuild.BuildSpec.from_object(dict(
                            version="0.2",
                            phases=dict(
                                build=dict(
                                    commands=[
                                        "ls -la",
                                        "cd provision/project/pipeline",
                                        "python3 deploy.py --target-name canary",
                                    ])),
                                artifacts={
                                "base-directory": ".",
                                "files": [
                                    "**/*"]},
                                environment=dict(buildImage=
                                codebuild.LinuxBuildImage.STANDARD_2_0))),
            environment_variables={
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=kwargs['env'].region)
            })
        
        policy_names = [
            "AWSCloudFormationFullAccess", 
            "AmazonS3FullAccess",
            "AWSGreengrassFullAccess",
            "IAMFullAccess",
        ]
        for policy_name in policy_names:
            cdk_deploy_canary.role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(policy_name)
            )
        
        cdk_deploy_main = codebuild.PipelineProject(
            self,
            "DeployMain",
            project_name="iot-gg-cicd-workshop-deploy-main",
            build_spec=codebuild.BuildSpec.from_object(dict(
                            version="0.2",
                            phases=dict(
                                build=dict(
                                    commands=[
                                        "ls -la",
                                        "cd provision/project/pipeline",
                                        "python3 deploy.py --target-name main",
                                    ])),
                                artifacts={
                                "base-directory": ".",
                                "files": [
                                    "**/*"]},
                                environment=dict(buildImage=
                                codebuild.LinuxBuildImage.STANDARD_2_0))),
            environment_variables={
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=kwargs['env'].region)
            })
        
        policy_names = [
            "AWSCloudFormationFullAccess", 
            "AmazonS3FullAccess",
            "AWSGreengrassFullAccess",
            "IAMFullAccess",
        ]
        for policy_name in policy_names:
            cdk_deploy_main.role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(policy_name)
            )

        source_output = codepipeline.Artifact()
        buildartifact_output = codepipeline.Artifact()

        cdk_build_output = codepipeline.Artifact("CdkBuildOutput")
        source_output = codepipeline.Artifact(artifact_name='source')
        pipeline_name = deploy_params['pipelineName']
        codepipeline.Pipeline(self,
                              "Pipeline",
                              pipeline_name=pipeline_name,
                              stages=[
                                  codepipeline.StageProps(stage_name="Source",
                                                          actions=[
                                                              codepipeline_actions.CodeCommitSourceAction(
                                                                  action_name="CodeCommit_Source",
                                                                  repository=code,
                                                                  branch=repository_branch,
                                                    output=source_output)]),
                                  codepipeline.StageProps(stage_name="Build_artifacts",
                                                          actions=[
                                                              codepipeline_actions.CodeDeployServerDeployAction(
                                                                deployment_group=code_deploy.ServerDeploymentGroup.from_server_deployment_group_attributes(
                                                                    self,
                                                                    "server_code_deploy_group",
                                                                    application=code_deploy.ServerApplication.from_server_application_name(self,"server_app",server_application_name="GreenGrassDeployment"),
                                                                    deployment_group_name="GreenGrassDeploymentGroup",
                                                                ),
                                                                action_name="Greengrass_build",
                                                                input=source_output)]),
                                  codepipeline.StageProps(stage_name="Deploy_in_greengrass_canary",
                                                          actions=[
                                                              codepipeline_actions.CodeBuildAction(
                                                                  action_name="Build_Package_Deploy_Canary",
                                                                  project=cdk_deploy_canary,
                                                                  input=source_output)]),
                                  codepipeline.StageProps(stage_name="Deploy_in_greengrass_main",
                                                          actions=[
                                                              codepipeline_actions.CodeBuildAction(
                                                                  action_name="Build_Package_Deploy_Main",
                                                                  project=cdk_deploy_main,
                                                                  input=source_output)]),
                              ]
                              )

