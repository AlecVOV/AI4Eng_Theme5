"""
SageMaker Pipeline — 5G Network Quality (Preprocessing → Clustering → Forecasting).

Steps:
  1. PreprocessingStep  — sklearn container, runs scripts/preprocess.py
     (loads raw CSVs, cleans, resamples, engineers features, exports cleaned_5g_data.csv)
  2. ClusteringTrainStep — sklearn container, runs scripts/train_clustering.py
     (KMeans on 9 spatial features, exports map_data.csv + model artefacts)
  3. ForecastTrainStep   — tensorflow container, runs scripts/train_forecasting.py
     (XGBoost + LSTM + CNN benchmark, 12-h forecast, exports forecast_data.csv + models)

Note: The forecasting script imports tensorflow + xgboost. We use the TensorFlow
training image for Step 3 (xgboost is pip-installed at runtime via requirements).
"""
import sagemaker
from sagemaker.inputs import TrainingInput
from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.estimator import Estimator
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

ROLE_ARN = "arn:aws:iam::677276113002:role/5g-sagemaker-execution-role"
REGION = "us-east-1"

session = sagemaker.Session()
bucket_raw = "5g-dashboard-raw-data"
bucket_cleaned = "5g-dashboard-cleaned-data"
bucket_artifacts = "5g-dashboard-artifacts"

# ── Container images ────────────────────────────────────────────
# Preprocessing & clustering use sklearn; forecasting needs TF + XGBoost.
sklearn_image = sagemaker.image_uris.retrieve("sklearn", REGION, version="1.2-1")
tensorflow_image = sagemaker.image_uris.retrieve(
    "tensorflow", REGION, version="2.12", py_version="py310",
    instance_type="ml.m5.large", image_scope="training",
)

# =================================================================
# Step 1 — Preprocessing (Processing Job)
# =================================================================
preprocessing_processor = ScriptProcessor(
    image_uri=sklearn_image,
    role=ROLE_ARN,
    instance_count=1,
    instance_type="ml.m5.large",
    command=["python3"],
)

preprocessing_step = ProcessingStep(
    name="PreprocessingStep",
    processor=preprocessing_processor,
    code="scripts/preprocess.py",
    inputs=[
        ProcessingInput(
            source=f"s3://{bucket_raw}/",
            destination="/opt/ml/processing/input",
        ),
    ],
    outputs=[
        ProcessingOutput(
            source="/opt/ml/processing/output",
            destination=f"s3://{bucket_cleaned}/latest/",
        ),
    ],
)

# =================================================================
# Step 2 — Clustering Training
# =================================================================
clustering_estimator = Estimator(
    image_uri=sklearn_image,
    role=ROLE_ARN,
    instance_count=1,
    instance_type="ml.m5.large",
    entry_point="scripts/train_clustering.py",
    output_path=f"s3://{bucket_artifacts}/models/clustering/",
    hyperparameters={"n-clusters": 3},
)

clustering_step = TrainingStep(
    name="ClusteringTrainStep",
    estimator=clustering_estimator,
    inputs={
        "training": TrainingInput(
            s3_data=f"s3://{bucket_cleaned}/latest/",
        ),
    },
)
clustering_step.add_depends_on([preprocessing_step])

# =================================================================
# Step 3 — Forecasting Training (TensorFlow + XGBoost)
# =================================================================
forecasting_estimator = Estimator(
    image_uri=tensorflow_image,
    role=ROLE_ARN,
    instance_count=1,
    instance_type="ml.m5.large",
    entry_point="scripts/train_forecasting.py",
    output_path=f"s3://{bucket_artifacts}/models/forecasting/",
)

forecasting_step = TrainingStep(
    name="ForecastTrainStep",
    estimator=forecasting_estimator,
    inputs={
        "training": TrainingInput(
            s3_data=f"s3://{bucket_cleaned}/latest/",
        ),
    },
)
forecasting_step.add_depends_on([preprocessing_step])

# =================================================================
# Pipeline Definition
# =================================================================
pipeline = Pipeline(
    name="5g-quality-pipeline",
    steps=[preprocessing_step, clustering_step, forecasting_step],
    sagemaker_session=session,
)

if __name__ == "__main__":
    pipeline.upsert(role_arn=ROLE_ARN)
    print("Pipeline created/updated successfully.")