from aws_cdk import (
    core,
    aws_iot as iot,
    custom_resources as cust_resource,
    aws_lambda as awslambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_codebuild as codebuild,
    aws_codedeploy as code_deploy,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_greengrassv2 as greengrassv2,
    aws_ssm as ssm
)
import uuid

class PipelineStack(core.Stack):
    """
    Utility to define PipelineStack
    """
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        code = codecommit.IRepository(
            self, "CodeRepo", repository_name="greengrass-iot-cicd-sample"
        )

        # create a server application
        serverApplication = code_deploy.ServerApplication(
            self, "MyDemoApplication", application_name="MyDemoApplication",
        )
        role_arn="arn:aws:iam::465906353389:role/codedeploy-iot-gg-sample-project-service-role"
        code_deploy.ServerDeploymentGroup(
            self,
            "CodeDeploymentGroup",
            application=serverApplication,
            deployment_group_name="MyDemoDeploymentGroup",
            role=iam.Role.from_role_arn(
                    self,
                    "role",
                    role_arn=role_arn
                ),
            deployment_config=code_deploy.ServerDeploymentConfig.ONE_AT_A_TIME,
            on_premise_instance_tags =code_deploy.InstanceTagSet(
                {"Name": ["JetsonNano"]},
            ),
        )
        inline_recipe = "HelloWorld-example-cpp.yaml"
        greengrass_policy_names = [
            "AWSGreengrassFullAccess",
            "GreengrassV2AllAccess",
        ]
        greengrass_component = greengrassv2.CfnComponentVersion(
            self,
            inline_recipe=inline_recipe
        )

        for policy_name in greengrass_policy_names:
            greengrass_component.role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(policy_name)
            )
        
        cdk_deploy_canary = codebuild.PipelineProject(
            self,
            "Deploy",
            project_name="iot-gg-cicd-workshop-deploy-canary",
            build_spec=codebuild.BuildSpec.from_object(dict(
                            version="0.2",
                            phases=dict(
                                build=dict(
                                    commands=[
                                        "ls -la",
                                        "cd provision/project/pipeline",
                                        "python3 deploy.py --target-arn arn:aws:iot:us-west-2:465906353389:thinggroup/canary --deployment-name iot-gg-canary",
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
            "AWSGreengrassV2FullAccess",
            "IAMFullAccess",
        ]
        for policy_name in policy_names:
            cdk_deploy_canary.role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(policy_name)
            )
        
        source_output = codepipeline.Artifact()
        cdk_build_output = codepipeline.Artifact("CdkBuildOutput")
        source_output = codepipeline.Artifact(artifact_name='source')
        codepipeline.Pipeline(self,
                              "Pipeline",
                              pipeline_name="iot-gg-cicd-workshop-pipeline-canary",
                              stages=[
                                  codepipeline.StageProps(stage_name="Source",
                                                          actions=[
                                                              codepipeline_actions.CodeCommitSourceAction(
                                                                  action_name="CodeCommit_Source",
                                                                  repository=code,
                                                                  output=source_output)]),
                                  codepipeline.StageProps(stage_name="Build_artifacts",
                                                          actions=[
                                                              codepipeline_actions.CodeDeployServerDeployAction(
                                                                deployment_group=code_deploy.ServerDeploymentGroup.from_server_deployment_group_attributes(
                                                                    self,
                                                                    "server_code_deploy_group",
                                                                    application=code_deploy.ServerApplication.from_server_application_name(self,"server_app",server_application_name="MyDemoApplication"),
                                                                    deployment_group_name="MyDemoDeploymentGroup",
                                                                ),
                                                                action_name="Greengrass_build",
                                                                input=source_output)]),
                                  codepipeline.StageProps(stage_name="Deploy_in_greengrass",
                                                          actions=[
                                                              codepipeline_actions.CodeBuildAction(
                                                                  action_name="Build_Package_Deploy",
                                                                  project=cdk_deploy_canary,
                                                                  input=source_output)]),
                              ]
                              )

        # cdk_deploy_prod = codebuild.PipelineProject(
        #     self,
        #     "DeployProd",
        #     project_name="iot-gg-cicd-workshop-deploy-main",
        #     build_spec=codebuild.BuildSpec.from_object(dict(
        #                     version="0.2",
        #                     phases=dict(
        #                         install=dict(
        #                             commands=[
        #                                 "apt-get install zip",
        #                                 "aws s3 cp s3://iot-gg-cicd-sample/deploy_package.zip prod_deploy.zip",
        #                                 "unzip -o prod_deploy.zip",
        #                                 "ls -la",
        #                             ]),
        #                         build=dict(
        #                             commands=[
        #                                 "ls -la",
        #                                 "make deploy-greengrass-prod",
        #                             ])),
        #                         artifacts={
        #                         "base-directory": ".",
        #                         "files": [
        #                             "**/*"]},
        #                         environment=dict(buildImage=
        #                         codebuild.LinuxBuildImage.STANDARD_2_0))))

        # add_policies(
        #     cdk_deploy_prod,
        #     [
        #         "AWSCloudFormationFullAccess",
        #         "AWSGreengrassFullAccess",
        #         "AmazonSSMFullAccess",
        #         "ResourceGroupsandTagEditorReadOnlyAccess",
        #         "AWSLambdaFullAccess"
        #     ])

        # prod_source_output = codepipeline.Artifact()
        # codepipeline.Pipeline(self,
        #                       "PipelineProd",
        #                       pipeline_name="iot-gg-cicd-workshop-pipeline-main",
        #                       stages=[
        #                           codepipeline.StageProps(stage_name="Source",
        #                                                   actions=[
        #                                                       codepipeline_actions.S3SourceAction(
        #                                                           action_name="S3_Source",
        #                                                           bucket=prod_deploy_param_bucket,
        #                                                           bucket_key="deploy_params.zip",
        #                                                           output=prod_source_output)]),
        #                           codepipeline.StageProps(stage_name="Deploy_GreenGrass_Prod",
        #                                                   actions=[
        #                                                       codepipeline_actions.CodeBuildAction(
        #                                                           action_name="Deploy_Prod",
        #                                                           project=cdk_deploy_prod,
        #                                                           input=prod_source_output)]),
        #                       ]
        #                       )
        # prod_source_bucket.grant_read_write(cdk_deploy_canary.role)
        # prod_source_bucket.grant_read(cdk_deploy_prod.role)
        # prod_deploy_param_bucket.grant_read_write(cdk_deploy_canary.role)
