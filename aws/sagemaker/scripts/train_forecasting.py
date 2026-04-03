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