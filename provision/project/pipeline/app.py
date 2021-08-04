"""
Cdk app
"""
from aws_cdk import core

from lib.greengrass_stack import GreengrassComponentDefinitions

app = core.App()
GreengrassComponentDefinitions(app, "s3trigger")

app.synth()
