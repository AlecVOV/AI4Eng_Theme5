"""Defines the SageMaker Pipeline for the 5G Quality project."""
import sagemaker
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.processing import ScriptProcessor
from sagemaker.estimator import Estimator

ROLE_ARN = "arn:aws:iam::677276113002:role/5g-sagemaker-execution-role"
REGION = "us-east-1"

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