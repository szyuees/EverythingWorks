import boto3
import json

bedrock = boto3.client('bedrock', region_name='us-east-1')
response = bedrock.list_foundation_models()

for model in response['modelSummaries']:
    print(f"Model ID: {model['modelId']}, Provider: {model['providerName']}")