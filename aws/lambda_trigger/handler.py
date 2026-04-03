import json
import boto3
import os

sagemaker = boto3.client("sagemaker")

PIPELINE_NAME = os.environ["SAGEMAKER_PIPELINE_NAME"]

def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        response = sagemaker.start_pipeline_execution(
            PipelineName=PIPELINE_NAME,
            PipelineParameters=[
                {"Name": "InputS3Uri", "Value": f"s3://{bucket}/{key}"},
            ],
        )

        print(f"Started pipeline execution: {response['PipelineExecutionArn']}")

    return {"statusCode": 200, "body": json.dumps("Pipeline triggered.")}