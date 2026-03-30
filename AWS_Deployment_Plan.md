# AWS Serverless Deployment Plan — 5G Network Quality Dashboard

> **COS40007 — AI For Engineering (Final Project)**
> **Architecture:** CloudFront + API Gateway + Lambda (Mangum) + S3 + SageMaker
> **Cost Target:** AWS Free Tier / near-zero cost

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Phase 1: IAM & Security Foundation](#phase-1-iam--security-foundation)
3. [Phase 2: Storage & ML Triggers](#phase-2-storage--ml-triggers)
4. [Phase 3: SageMaker Pipeline](#phase-3-sagemaker-pipeline)
5. [Phase 4: Serverless Backend (ECR + Lambda + API Gateway)](#phase-4-serverless-backend-ecr--lambda--api-gateway)
6. [Phase 5: Frontend Deployment (S3 + CloudFront)](#phase-5-frontend-deployment-s3--cloudfront)
7. [Phase 6: Testing Checklist](#phase-6-testing-checklist)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SERVING LAYER                                   │
│                                                                         │
│  User ──► CloudFront (CDN) ──► S3 (frontend dist/)                     │
│              │                                                          │
│              └──► /api/* ──► API Gateway (HTTP API)                     │
│                                  │                                      │
│                                  ▼                                      │
│                        Lambda (ECR container)                           │
│                        Mangum → FastAPI                                 │
│                              │                                          │
│                              ├──► S3 Artifacts (load .pkl models)       │
│                              └──► Supabase (verify JWT)                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                         MLOps PIPELINE                                  │
│                                                                         │
│  Admin Upload ──► S3 Raw Data ──► Lambda Trigger                       │
│                                       │                                 │
│                                       ▼                                 │
│                              SageMaker Pipelines                        │
│                              ├── Processing Job (clean + merge)         │
│                              └── Training Job (KMeans + XGBoost)        │
│                                       │                                 │
│                                       ▼                                 │
│                              S3 Artifacts (.pkl models)                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### S3 Bucket Layout

| Bucket | Purpose |
|---|---|
| `5g-dashboard-raw-data` | Raw CSV uploads from admin |
| `5g-dashboard-cleaned-data` | Cleaned/merged CSVs (Feature Store) |
| `5g-dashboard-artifacts` | Trained `.pkl` model files + `map_data.csv` + `forecast_data.csv` |
| `5g-dashboard-frontend` | Vue 3 production build (`dist/`) |

---

## Phase 1: IAM & Security Foundation

### 1.1 — Create IAM Roles

Three execution roles are needed. Each follows the principle of least privilege.

#### Role A: `5g-pipeline-trigger-lambda-role`

Purpose: The Lambda function triggered by S3 upload events. It starts the SageMaker pipeline.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadRawBucket",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::5g-dashboard-raw-data/*"
    },
    {
      "Sid": "StartSageMakerPipeline",
      "Effect": "Allow",
      "Action": [
        "sagemaker:StartPipelineExecution",
        "sagemaker:DescribePipelineExecution"
      ],
      "Resource": "arn:aws:sagemaker:*:*:pipeline/5g-quality-pipeline*"
    },
    {
      "Sid": "Logging",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

Trust policy (same for all three Lambda roles):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

#### Role B: `5g-sagemaker-execution-role`

Purpose: SageMaker Processing and Training jobs. Needs read/write on all three S3 buckets and ECR image pull.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ReadWrite",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::5g-dashboard-raw-data",
        "arn:aws:s3:::5g-dashboard-raw-data/*",
        "arn:aws:s3:::5g-dashboard-cleaned-data",
        "arn:aws:s3:::5g-dashboard-cleaned-data/*",
        "arn:aws:s3:::5g-dashboard-artifacts",
        "arn:aws:s3:::5g-dashboard-artifacts/*"
      ]
    },
    {
      "Sid": "ECRPull",
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Logging",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

Trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "sagemaker.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

#### Role C: `5g-fastapi-lambda-role`

Purpose: The FastAPI Lambda function. Reads model artifacts from S3 and writes CloudWatch logs.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadArtifacts",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::5g-dashboard-artifacts/*"
    },
    {
      "Sid": "Logging",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### 1.2 — AWS CLI Commands (create the roles)

```bash
# Role A — Pipeline Trigger Lambda
aws iam create-role \
  --role-name 5g-pipeline-trigger-lambda-role \
  --assume-role-policy-document file://trust-lambda.json

aws iam put-role-policy \
  --role-name 5g-pipeline-trigger-lambda-role \
  --policy-name 5g-pipeline-trigger-policy \
  --policy-document file://policy-trigger-lambda.json

# Role B — SageMaker Execution
aws iam create-role \
  --role-name 5g-sagemaker-execution-role \
  --assume-role-policy-document file://trust-sagemaker.json

aws iam put-role-policy \
  --role-name 5g-sagemaker-execution-role \
  --policy-name 5g-sagemaker-policy \
  --policy-document file://policy-sagemaker.json

# Role C — FastAPI Lambda
aws iam create-role \
  --role-name 5g-fastapi-lambda-role \
  --assume-role-policy-document file://trust-lambda.json

aws iam put-role-policy \
  --role-name 5g-fastapi-lambda-role \
  --policy-name 5g-fastapi-lambda-policy \
  --policy-document file://policy-fastapi-lambda.json
```

---

## Phase 2: Storage & ML Triggers

### 2.1 — Create S3 Buckets

```bash
AWS_REGION="ap-southeast-2"  # Sydney — adjust to your region

# Raw uploads
aws s3api create-bucket \
  --bucket 5g-dashboard-raw-data \
  --region $AWS_REGION \
  --create-bucket-configuration LocationConstraint=$AWS_REGION

# Cleaned / feature store
aws s3api create-bucket \
  --bucket 5g-dashboard-cleaned-data \
  --region $AWS_REGION \
  --create-bucket-configuration LocationConstraint=$AWS_REGION

# Model artifacts + inference CSVs
aws s3api create-bucket \
  --bucket 5g-dashboard-artifacts \
  --region $AWS_REGION \
  --create-bucket-configuration LocationConstraint=$AWS_REGION
```

### 2.2 — Block Public Access (all three buckets)

```bash
for BUCKET in 5g-dashboard-raw-data 5g-dashboard-cleaned-data 5g-dashboard-artifacts; do
  aws s3api put-public-access-block \
    --bucket $BUCKET \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
done
```

### 2.3 — Upload Existing Data to S3

```bash
# Upload the 138 raw CSVs
aws s3 sync backend/data/ s3://5g-dashboard-raw-data/ --exclude "map_data.csv"

# Upload current model artifacts
aws s3 sync backend/models/ s3://5g-dashboard-artifacts/models/

# Upload inference outputs
aws s3 cp backend/data/map_data.csv s3://5g-dashboard-artifacts/data/map_data.csv
aws s3 cp backend/metrics/forecast_data.csv s3://5g-dashboard-artifacts/metrics/forecast_data.csv
```

### 2.4 — Create Pipeline Trigger Lambda

Create a minimal Lambda function that triggers the SageMaker pipeline when a new CSV is uploaded:

**`lambda_trigger/handler.py`**:

```python
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
```

### 2.5 — Deploy Trigger Lambda & Add S3 Event

```bash
# Package and create the trigger Lambda
cd lambda_trigger
zip function.zip handler.py
aws lambda create-function \
  --function-name 5g-pipeline-trigger \
  --runtime python3.10 \
  --handler handler.lambda_handler \
  --role arn:aws:iam::ACCOUNT_ID:role/5g-pipeline-trigger-lambda-role \
  --zip-file fileb://function.zip \
  --environment "Variables={SAGEMAKER_PIPELINE_NAME=5g-quality-pipeline}" \
  --timeout 30

# Grant S3 permission to invoke the Lambda
aws lambda add-permission \
  --function-name 5g-pipeline-trigger \
  --statement-id s3-invoke \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::5g-dashboard-raw-data

# Configure S3 ObjectCreated trigger
aws s3api put-bucket-notification-configuration \
  --bucket 5g-dashboard-raw-data \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "LambdaFunctionArn": "arn:aws:lambda:REGION:ACCOUNT_ID:function:5g-pipeline-trigger",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [{"Name": "suffix", "Value": ".csv"}]
        }
      }
    }]
  }'
```

---

## Phase 3: SageMaker Pipeline

### 3.1 — Strategy: Port Local Notebooks to SageMaker Jobs

Our three local Jupyter notebooks map directly to SageMaker pipeline steps:

| Local Notebook | SageMaker Step | Job Type |
|---|---|---|
| `1_data_preprocessing.ipynb` | `PreprocessingStep` | Processing Job |
| `2_model_clustering.ipynb` | `ClusteringTrainStep` | Training Job |
| `3_model_forecasting.ipynb` | `ForecastTrainStep` | Training Job |

### 3.2 — Convert Notebooks to Scripts

For each notebook, extract the executable cells into a standalone `.py` script that reads from/writes to S3 paths passed via CLI arguments.

**`sagemaker/scripts/preprocess.py`** (skeleton):

```python
"""SageMaker Processing Job — Data Preprocessing."""
import argparse
import os
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=str, default="/opt/ml/processing/input")
    parser.add_argument("--output-dir", type=str, default="/opt/ml/processing/output")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load all CSVs from input directory
    csv_files = sorted(input_dir.glob("*.csv"))
    dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)

    # 2. Clean invalid GPS coordinates (latitude=99, longitude=999)
    df = df[(df["latitude"] != 99) & (df["longitude"] != 999)]

    # 3. Clean timeout values (svr1-svr4 = 1000)
    for col in ["svr1", "svr2", "svr3", "svr4"]:
        if col in df.columns:
            df = df[df[col] != 1000]

    # 4. Drop rows with NaN in critical columns
    df = df.dropna(subset=["latitude", "longitude"])

    # 5. Save cleaned output
    df.to_csv(output_dir / "cleaned_data.csv", index=False)
    print(f"Preprocessing complete. Output rows: {len(df)}")

if __name__ == "__main__":
    main()
```

**`sagemaker/scripts/train_clustering.py`** (skeleton):

```python
"""SageMaker Training Job — KMeans Clustering."""
import argparse
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=str, default="/opt/ml/input/data/training")
    parser.add_argument("--model-dir", type=str, default="/opt/ml/model")
    parser.add_argument("--output-dir", type=str, default="/opt/ml/output/data")
    parser.add_argument("--n-clusters", type=int, default=3)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    model_dir = Path(args.model_dir)
    output_dir = Path(args.output_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load cleaned data
    df = pd.read_csv(input_dir / "cleaned_data.csv")

    # 2. Select features and scale
    features = df[["latitude", "longitude"]].copy()  # extend with signal cols as needed
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    # 3. Train KMeans
    model = KMeans(n_clusters=args.n_clusters, random_state=42, n_init=10)
    model.fit(X_scaled)
    df["cluster"] = model.labels_

    # 4. Save artifacts
    joblib.dump(model, model_dir / "clustering_model.pkl")
    joblib.dump(scaler, model_dir / "clustering_scaler.pkl")

    # 5. Save map_data.csv for the API
    df[["latitude", "longitude", "cluster"]].rename(
        columns={"latitude": "lat", "longitude": "lng"}
    ).to_csv(output_dir / "map_data.csv", index=False)

    print(f"Clustering complete. Clusters: {np.bincount(model.labels_)}")

if __name__ == "__main__":
    main()
```

**`sagemaker/scripts/train_forecasting.py`** (skeleton):

```python
"""SageMaker Training Job — XGBoost Time-Series Forecasting."""
import argparse
import joblib
import pandas as pd
import xgboost as xgb
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=str, default="/opt/ml/input/data/training")
    parser.add_argument("--model-dir", type=str, default="/opt/ml/model")
    parser.add_argument("--output-dir", type=str, default="/opt/ml/output/data")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    model_dir = Path(args.model_dir)
    output_dir = Path(args.output_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load cleaned data
    df = pd.read_csv(input_dir / "cleaned_data.csv", parse_dates=["timestamp"])
    df = df.sort_values("timestamp")

    # 2. Feature engineering — temporal features
    df["hour"] = df["timestamp"].dt.hour
    df["dayofweek"] = df["timestamp"].dt.dayofweek

    # 3. Train throughput model
    feature_cols = ["hour", "dayofweek"]  # extend as needed
    X = df[feature_cols]

    throughput_model = xgb.XGBRegressor(objective="reg:squarederror", n_estimators=200)
    throughput_model.fit(X, df["download_mbps"])
    joblib.dump(throughput_model, model_dir / "xgboost_download_mbps.pkl")

    # 4. Train latency model
    latency_model = xgb.XGBRegressor(objective="reg:squarederror", n_estimators=200)
    latency_model.fit(X, df["avg_latency"])
    joblib.dump(latency_model, model_dir / "xgboost_avg_latency.pkl")

    # 5. Generate forecast CSV
    # (Generate future timestamps and predict)
    forecast_df = pd.DataFrame()  # populate with predictions
    forecast_df.to_csv(output_dir / "forecast_data.csv", index=False)

    print("Forecasting training complete.")

if __name__ == "__main__":
    main()
```

### 3.3 — Define SageMaker Pipeline (Python SDK)

**`sagemaker/pipeline_definition.py`**:

```python
"""Defines the SageMaker Pipeline for the 5G Quality project."""
import sagemaker
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.processing import ScriptProcessor
from sagemaker.estimator import Estimator

ROLE_ARN = "arn:aws:iam::ACCOUNT_ID:role/5g-sagemaker-execution-role"
REGION = "ap-southeast-2"

session = sagemaker.Session()
bucket_raw = "5g-dashboard-raw-data"
bucket_cleaned = "5g-dashboard-cleaned-data"
bucket_artifacts = "5g-dashboard-artifacts"

# --- Step 1: Preprocessing ---
sklearn_processor = ScriptProcessor(
    image_uri=sagemaker.image_uris.retrieve("sklearn", REGION, version="1.2-1"),
    role=ROLE_ARN,
    instance_count=1,
    instance_type="ml.t3.medium",
    command=["python3"],
)

preprocessing_step = ProcessingStep(
    name="PreprocessingStep",
    processor=sklearn_processor,
    code="scripts/preprocess.py",
    inputs=[
        sagemaker.processing.ProcessingInput(
            source=f"s3://{bucket_raw}/",
            destination="/opt/ml/processing/input",
        )
    ],
    outputs=[
        sagemaker.processing.ProcessingOutput(
            source="/opt/ml/processing/output",
            destination=f"s3://{bucket_cleaned}/latest/",
        )
    ],
)

# --- Step 2: Clustering Training ---
clustering_estimator = Estimator(
    image_uri=sagemaker.image_uris.retrieve("sklearn", REGION, version="1.2-1"),
    role=ROLE_ARN,
    instance_count=1,
    instance_type="ml.t3.medium",
    entry_point="scripts/train_clustering.py",
    output_path=f"s3://{bucket_artifacts}/models/clustering/",
)

clustering_step = TrainingStep(
    name="ClusteringTrainStep",
    estimator=clustering_estimator,
    inputs={
        "training": sagemaker.inputs.TrainingInput(
            s3_data=f"s3://{bucket_cleaned}/latest/",
        )
    },
)
clustering_step.add_depends_on([preprocessing_step])

# --- Step 3: Forecasting Training ---
forecasting_estimator = Estimator(
    image_uri=sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1"),
    role=ROLE_ARN,
    instance_count=1,
    instance_type="ml.t3.medium",
    entry_point="scripts/train_forecasting.py",
    output_path=f"s3://{bucket_artifacts}/models/forecasting/",
)

forecasting_step = TrainingStep(
    name="ForecastTrainStep",
    estimator=forecasting_estimator,
    inputs={
        "training": sagemaker.inputs.TrainingInput(
            s3_data=f"s3://{bucket_cleaned}/latest/",
        )
    },
)
forecasting_step.add_depends_on([preprocessing_step])

# --- Pipeline Definition ---
pipeline = Pipeline(
    name="5g-quality-pipeline",
    steps=[preprocessing_step, clustering_step, forecasting_step],
    sagemaker_session=session,
)

if __name__ == "__main__":
    pipeline.upsert(role_arn=ROLE_ARN)
    print("Pipeline created/updated successfully.")
```

### 3.4 — Register the Pipeline

```bash
cd sagemaker
pip install sagemaker boto3
python pipeline_definition.py
```

---

## Phase 4: Serverless Backend (ECR + Lambda + API Gateway)

### 4.1 — Update the Backend Dockerfile for Lambda

The existing `backend/Dockerfile` runs Uvicorn. For Lambda, we need to use the AWS Lambda container runtime. Create a Lambda-specific Dockerfile:

**`backend/Dockerfile.lambda`**:

```dockerfile
FROM public.ecr.aws/lambda/python:3.10

# Copy requirements and install
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/
COPY main.py ${LAMBDA_TASK_ROOT}/
COPY .env ${LAMBDA_TASK_ROOT}/

# Copy model artifacts and data for inference
# (In production, these would be loaded from S3 at runtime)
COPY models/ ${LAMBDA_TASK_ROOT}/models/
COPY data/map_data.csv ${LAMBDA_TASK_ROOT}/data/map_data.csv
COPY metrics/forecast_data.csv ${LAMBDA_TASK_ROOT}/metrics/forecast_data.csv

# Mangum handler: app/main.py defines `handler = Mangum(app)`
CMD ["app.main.handler"]
```

### 4.2 — Create ECR Repository

```bash
AWS_REGION="ap-southeast-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr create-repository \
  --repository-name 5g-dashboard-backend \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true
```

### 4.3 — Build & Push Docker Image to ECR

```bash
# Authenticate Docker with ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and tag
cd backend
docker build -f Dockerfile.lambda -t 5g-dashboard-backend .
docker tag 5g-dashboard-backend:latest \
  $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/5g-dashboard-backend:latest

# Push
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/5g-dashboard-backend:latest
```

### 4.4 — Create the FastAPI Lambda Function

```bash
aws lambda create-function \
  --function-name 5g-dashboard-api \
  --package-type Image \
  --code ImageUri=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/5g-dashboard-backend:latest \
  --role arn:aws:iam::$ACCOUNT_ID:role/5g-fastapi-lambda-role \
  --memory-size 512 \
  --timeout 30 \
  --environment "Variables={
    RESEND_API_KEY=re_XXXXXXXXX,
    CONTACT_TO_EMAIL=your-email@example.com,
    S3_ARTIFACTS_BUCKET=5g-dashboard-artifacts
  }"
```

> **Security note:** For production, store `RESEND_API_KEY` in AWS Secrets Manager and reference
> it via the Lambda environment configuration, rather than passing it directly.

### 4.5 — Set Environment Variables on the Lambda

If you need to update environment variables after creation:

```bash
aws lambda update-function-configuration \
  --function-name 5g-dashboard-api \
  --environment "Variables={
    RESEND_API_KEY=re_XXXXXXXXX,
    CONTACT_TO_EMAIL=your-email@example.com,
    S3_ARTIFACTS_BUCKET=5g-dashboard-artifacts
  }"
```

### 4.6 — Create HTTP API Gateway

```bash
# Create the HTTP API
API_ID=$(aws apigatewayv2 create-api \
  --name 5g-dashboard-api-gw \
  --protocol-type HTTP \
  --cors-configuration '{
    "AllowOrigins": ["https://YOUR_CLOUDFRONT_DOMAIN"],
    "AllowMethods": ["GET", "POST", "OPTIONS"],
    "AllowHeaders": ["Content-Type", "Authorization"],
    "MaxAge": 3600
  }' \
  --query ApiId --output text)

echo "API ID: $API_ID"
```

### 4.7 — Create Lambda Integration

```bash
LAMBDA_ARN="arn:aws:lambda:$AWS_REGION:$ACCOUNT_ID:function:5g-dashboard-api"

INTEGRATION_ID=$(aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri $LAMBDA_ARN \
  --payload-format-version 2.0 \
  --query IntegrationId --output text)

echo "Integration ID: $INTEGRATION_ID"
```

### 4.8 — Create Catch-All Route (`ANY /{proxy+}`)

```bash
# Catch-all route — forwards every path/method to FastAPI via Mangum
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "ANY /{proxy+}" \
  --target "integrations/$INTEGRATION_ID"

# Also add the root route
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "ANY /" \
  --target "integrations/$INTEGRATION_ID"
```

### 4.9 — Grant API Gateway Permission to Invoke Lambda

```bash
aws lambda add-permission \
  --function-name 5g-dashboard-api \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$AWS_REGION:$ACCOUNT_ID:$API_ID/*"
```

### 4.10 — Deploy the API (create `$default` stage)

```bash
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name '$default' \
  --auto-deploy
```

The API will be available at:
```
https://{API_ID}.execute-api.{REGION}.amazonaws.com/
```

Test it:
```bash
curl https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/
# Expected: {"message":"5G Network Quality API is running."}

curl https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/api/map-data
# Expected: JSON array of cluster data
```

---

## Phase 5: Frontend Deployment (S3 + CloudFront)

### 5.1 — Build the Frontend

```bash
cd frontend

# Set the API base URL to the API Gateway endpoint
export VITE_API_BASE_URL="https://{API_ID}.execute-api.{REGION}.amazonaws.com"

# Build production bundle
npm run build
```

This outputs a static site to `frontend/dist/`.

### 5.2 — Create Frontend S3 Bucket

```bash
aws s3api create-bucket \
  --bucket 5g-dashboard-frontend \
  --region $AWS_REGION \
  --create-bucket-configuration LocationConstraint=$AWS_REGION

# Block all public access (CloudFront will use OAC)
aws s3api put-public-access-block \
  --bucket 5g-dashboard-frontend \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

### 5.3 — Upload the Build

```bash
aws s3 sync frontend/dist/ s3://5g-dashboard-frontend/ --delete
```

### 5.4 — Create CloudFront Distribution with OAC

```bash
# Step 1: Create Origin Access Control
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{
    "Name": "5g-dashboard-oac",
    "OriginAccessControlOriginType": "s3",
    "SigningBehavior": "always",
    "SigningProtocol": "sigv4"
  }' \
  --query 'OriginAccessControl.Id' --output text)

echo "OAC ID: $OAC_ID"
```

Create the CloudFront distribution config JSON file:

**`cloudfront-config.json`**:

```json
{
  "CallerReference": "5g-dashboard-2026",
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 2,
    "Items": [
      {
        "Id": "S3-frontend",
        "DomainName": "5g-dashboard-frontend.s3.ap-southeast-2.amazonaws.com",
        "S3OriginConfig": { "OriginAccessIdentity": "" },
        "OriginAccessControlId": "OAC_ID_PLACEHOLDER"
      },
      {
        "Id": "APIGateway-backend",
        "DomainName": "API_ID_PLACEHOLDER.execute-api.ap-southeast-2.amazonaws.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "https-only"
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-frontend",
    "ViewerProtocolPolicy": "redirect-to-https",
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"]
    },
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": { "Forward": "none" }
    }
  },
  "CacheBehaviors": {
    "Quantity": 1,
    "Items": [
      {
        "PathPattern": "/api/*",
        "TargetOriginId": "APIGateway-backend",
        "ViewerProtocolPolicy": "redirect-to-https",
        "AllowedMethods": {
          "Quantity": 7,
          "Items": ["GET", "HEAD", "OPTIONS", "PUT", "PATCH", "POST", "DELETE"]
        },
        "ForwardedValues": {
          "QueryString": true,
          "Cookies": { "Forward": "none" },
          "Headers": {
            "Quantity": 2,
            "Items": ["Authorization", "Content-Type"]
          }
        },
        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
        "OriginRequestPolicyId": "b689b0a8-53d0-40ab-baf2-68738e2966ac",
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 0
      }
    ]
  },
  "CustomErrorResponses": {
    "Quantity": 1,
    "Items": [
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 0
      }
    ]
  },
  "Enabled": true,
  "Comment": "5G Network Quality Dashboard"
}
```

> **Key points:**
> - The `404 → /index.html` custom error response enables Vue Router's history mode.
> - The `/api/*` cache behavior routes API calls to API Gateway with caching disabled.
> - Replace `OAC_ID_PLACEHOLDER` and `API_ID_PLACEHOLDER` with actual values.

```bash
aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json
```

### 5.5 — Add S3 Bucket Policy for CloudFront OAC

```bash
DISTRIBUTION_ARN="arn:aws:cloudfront::$ACCOUNT_ID:distribution/DISTRIBUTION_ID"

aws s3api put-bucket-policy \
  --bucket 5g-dashboard-frontend \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "AllowCloudFrontOAC",
      "Effect": "Allow",
      "Principal": { "Service": "cloudfront.amazonaws.com" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::5g-dashboard-frontend/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "'"$DISTRIBUTION_ARN"'"
        }
      }
    }]
  }'
```

### 5.6 — Update Frontend CORS

Once CloudFront is live, update the API Gateway CORS and the FastAPI CORS middleware to include the CloudFront domain:

```bash
# Update API Gateway CORS
aws apigatewayv2 update-api \
  --api-id $API_ID \
  --cors-configuration '{
    "AllowOrigins": ["https://d1234abcdef.cloudfront.net"],
    "AllowMethods": ["GET", "POST", "OPTIONS"],
    "AllowHeaders": ["Content-Type", "Authorization"],
    "MaxAge": 3600
  }'
```

Also update `backend/app/main.py` CORS origins to include the CloudFront domain.

---

## Phase 6: Testing Checklist

### End-to-End Verification

Run through each check after deployment. Mark each item as it passes.

#### 6.1 — Backend API (Lambda)

| # | Test | Command / Action | Expected |
|---|---|---|---|
| 1 | Health check | `curl https://<api-gw-url>/` | `{"message":"5G Network Quality API is running."}` |
| 2 | Map data endpoint | `curl https://<api-gw-url>/api/map-data` | JSON array with `lat`, `lng`, `cluster` fields |
| 3 | Forecast endpoint | `curl https://<api-gw-url>/api/forecast-data` | JSON array with `timestamp`, `predicted_throughput`, `predicted_latency` |
| 4 | Contact email | `curl -X POST https://<api-gw-url>/api/contact -H 'Content-Type: application/json' -d '{"name":"Test","email":"test@test.com","message":"Hello"}'` | `{"status":"sent"}` |
| 5 | CORS headers | `curl -I -X OPTIONS https://<api-gw-url>/api/map-data -H 'Origin: https://<cloudfront-domain>'` | `Access-Control-Allow-Origin` header present |
| 6 | Invalid route returns 404 | `curl https://<api-gw-url>/api/nonexistent` | HTTP 404 |
| 7 | Cold start latency | Time the first request after 15 min idle | < 10s acceptable for free tier |

#### 6.2 — Frontend (CloudFront + S3)

| # | Test | Action | Expected |
|---|---|---|---|
| 1 | Dashboard loads | Visit `https://<cloudfront-domain>/` | Map + chart render with live data |
| 2 | Map markers display | Inspect map panel | Coloured circle markers with cluster popups |
| 3 | Chart renders | Inspect chart panel | Dual-axis line chart (throughput + latency) |
| 4 | About page | Navigate to `/about` | Team cards with scroll animations |
| 5 | Architecture page | Navigate to `/architecture` | MLOps pipeline + AWS architecture components |
| 6 | Contact form | Submit a test message via `/contact` | Success confirmation card |
| 7 | Login flow | Navigate to `/login`, sign in with Supabase | Redirects to `/admin` |
| 8 | Admin panel | Access `/admin` while authenticated | Data upload + artifact viewer |
| 9 | Auth guard | Visit `/admin` while logged out | Redirected to `/login` |
| 10 | 404 page | Visit `/nonexistent` | Custom 404 page renders |
| 11 | Vue Router history mode | Refresh on `/about` | Page loads (no S3 404) |
| 12 | HTTPS redirect | Visit `http://<cloudfront-domain>/` | Redirected to HTTPS |

#### 6.3 — MLOps Pipeline

| # | Test | Action | Expected |
|---|---|---|---|
| 1 | S3 upload trigger | Upload a CSV to `s3://5g-dashboard-raw-data/` | CloudWatch logs show Lambda invoked |
| 2 | Pipeline starts | Check SageMaker console | Pipeline execution in "Executing" status |
| 3 | Processing job | Wait for completion | `cleaned_data.csv` in `s3://5g-dashboard-cleaned-data/` |
| 4 | Training jobs | Wait for completion | New `.pkl` files in `s3://5g-dashboard-artifacts/models/` |
| 5 | Updated predictions | Call `/api/map-data` after pipeline | Data reflects new model outputs |

#### 6.4 — Security

| # | Test | Expected |
|---|---|---|
| 1 | S3 buckets not publicly accessible | `aws s3api get-public-access-block` returns all `true` |
| 2 | Lambda env vars not exposed | No secrets in API responses |
| 3 | CORS locked to CloudFront domain | Requests from other origins rejected |
| 4 | Admin routes protected | `/admin` redirects unauthenticated users |
| 5 | Supabase JWT validation | Invalid/expired tokens return 401 |

---

## Cost Estimate (Free Tier)

| Service | Free Tier Allowance | Our Usage (est.) |
|---|---|---|
| Lambda | 1M requests + 400,000 GB-seconds/month | < 10K requests/month |
| API Gateway | 1M HTTP API calls/month (first 12 months) | < 10K calls/month |
| S3 | 5 GB storage, 20K GET, 2K PUT | < 1 GB total |
| CloudFront | 1 TB transfer, 10M requests/month (first 12 months) | < 1 GB transfer |
| SageMaker | 250 hrs `ml.t3.medium`/month (first 2 months) | < 5 hrs/month |
| ECR | 500 MB storage (first 12 months) | ~200 MB image |
| **Total** | | **$0.00/month** (within free tier) |

---

## Quick Reference — Key ARNs & URLs

Fill these in as you deploy:

| Resource | Value |
|---|---|
| AWS Account ID | `____________` |
| AWS Region | `ap-southeast-2` |
| ECR Repository URI | `ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/5g-dashboard-backend` |
| FastAPI Lambda ARN | `arn:aws:lambda:REGION:ACCOUNT_ID:function:5g-dashboard-api` |
| Pipeline Trigger Lambda ARN | `arn:aws:lambda:REGION:ACCOUNT_ID:function:5g-pipeline-trigger` |
| API Gateway URL | `https://API_ID.execute-api.REGION.amazonaws.com` |
| CloudFront Domain | `https://d1234abcdef.cloudfront.net` |
| S3 Raw Data | `s3://5g-dashboard-raw-data` |
| S3 Cleaned Data | `s3://5g-dashboard-cleaned-data` |
| S3 Artifacts | `s3://5g-dashboard-artifacts` |
| S3 Frontend | `s3://5g-dashboard-frontend` |
| SageMaker Pipeline | `5g-quality-pipeline` |
| Supabase Project URL | `____________` |
