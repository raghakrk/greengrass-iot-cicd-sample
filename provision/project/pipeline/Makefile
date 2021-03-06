export CDK_DEFAULT_ACCOUNT = $(shell aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION = $(shell aws configure get region)
SHELL := /bin/bash

init: 
	@echo Deploy Account is $(CDK_DEFAULT_ACCOUNT)
	@echo Deploy Region is $(CDK_DEFAULT_REGION)
	python3 -m venv venv/
	venv/bin/python3 --version
	venv/bin/pip install git-remote-codecommit
	venv/bin/pip install -r requirements.txt
	npx cdk bootstrap aws://$(CDK_DEFAULT_ACCOUNT)/$(CDK_DEFAULT_REGION)

clean:
	@echo Deploy Account is $(CDK_DEFAULT_ACCOUNT)
	@echo Deploy Region is $(CDK_DEFAULT_REGION)
	rm -rf dist || true
	rm -rf out || true
	rm -rf venv || true
	rm -rf lib/*.egg-info || true
	rm -rf cdk.out || true
	rm cdk.context.json || true

deploy-pipeline:
	npx cdk deploy greengrasspipeline --require-approval never

destroy-pipeline:
	npx cdk destroy greengrasspipeline

list: 
	npx cdk list

all: clean init deploy-pipeline
