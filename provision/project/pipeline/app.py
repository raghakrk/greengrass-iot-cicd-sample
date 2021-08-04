"""
Cdk app
"""
from aws_cdk import core

from lib.greengrass_stack import PipelineStack

CDK_DEFAULT_ACCOUNT='465906353389'
CDK_DEFAULT_REGION='us-west-2'

env = core.Environment(
    account=CDK_DEFAULT_ACCOUNT,
    region=CDK_DEFAULT_REGION,
)

app = core.App()
PipelineStack(app, "greengrasspipeline", env=env)

app.synth()
