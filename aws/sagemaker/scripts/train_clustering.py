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


