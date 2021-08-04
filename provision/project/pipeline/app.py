"""
Cdk app
"""
from aws_cdk import core

from lib.greengrass_stack import PipelineStack

app = core.App()
PipelineStack(app, "greengrass_pipeline")

app.synth()
