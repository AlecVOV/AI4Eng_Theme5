"""
SageMaker Training Job — K-Means Clustering (Spatial Quality Labels).

Replicates the full pipeline from Notebook 2 (2_model_clustering.ipynb):
  1. Load cleaned_5g_data.csv
  2. Reconstruct base features dropped by feature-selection
  3. Aggregate per square_id (9 network-quality features)
  4. K-Means (k=3) + deterministic quality relabelling (0=Poor, 1=Medium, 2=Good)
  5. Export map_data.csv + model artefacts (clustering_model.pkl, clustering_scaler.pkl)

Frontend contract: backend/data/map_data.csv with columns lat, lng, cluster (∈ {0,1,2}).
"""
import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

CLUSTER_FEATURES = [
    "download_mbps_mean", "download_mbps_std",
    "avg_latency_mean", "avg_latency_std",
    "cwnd_mean",
    "retransmission_rate_mean",
    "jitter_mean",
    "latency_spread_mean",
    "congestion_indicator_mean",
]

LABEL_MAP = {0: "Yếu (Poor)", 1: "Trung bình (Medium)", 2: "Tốt (Good)"}


def main() -> None:
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

    # ================================================================
    # Step 1 — Load cleaned data
    # ================================================================
    df = pd.read_csv(input_dir / "cleaned_5g_data.csv", low_memory=False)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    print(f"Loaded: {len(df):,} rows × {df.shape[1]} columns")

    # ================================================================
    # Step 2 — Reconstruct base features
    # ================================================================
    # These were dropped in Notebook 1's feature-selection step (|r| > 0.95)
    # but are needed for interpretable spatial clustering.
    df["download_mbps"] = np.expm1(df["log_download"])
    df["avg_latency"] = df["avg_latency_lag1"]
    df["cwnd"] = pd.to_numeric(df["CWnd"], errors="coerce").fillna(0)

    # ================================================================
    # Step 3 — Spatial aggregation per square_id
    # ================================================================
    agg_dict = {
        "latitude": "mean",
        "longitude": "mean",
        "download_mbps": ["mean", "std"],
        "avg_latency": ["mean", "std"],
        "cwnd": "mean",
        "retransmission_rate": "mean",
        "jitter": "mean",
        "latency_spread": "mean",
        "congestion_indicator": "mean",
    }

    grid = df.groupby("square_id").agg(agg_dict)
    grid.columns = ["_".join(col).strip("_") for col in grid.columns]
    grid.rename(columns={
        "latitude_mean": "lat",
        "longitude_mean": "lng",
    }, inplace=True)
    grid.reset_index(inplace=True)
    print(f"Grid squares: {len(grid)}")

    # ================================================================
    # Step 4 — K-Means clustering + deterministic relabelling
    # ================================================================
    X_raw = grid[CLUSTER_FEATURES].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    kmeans = KMeans(n_clusters=args.n_clusters, random_state=42, n_init=10)
    grid["cluster_raw"] = kmeans.fit_predict(X_scaled)

    # Deterministic re-labelling: 0=Poor, 1=Medium, 2=Good
    # Rank by composite score: higher download + lower latency = better
    centroid_df = pd.DataFrame(
        scaler.inverse_transform(kmeans.cluster_centers_),
        columns=CLUSTER_FEATURES,
    )
    centroid_df["_quality_score"] = (
        centroid_df["download_mbps_mean"] - centroid_df["avg_latency_mean"]
    )
    sorted_labels = centroid_df["_quality_score"].sort_values().index.tolist()
    remap = {old: new for new, old in enumerate(sorted_labels)}
    grid["cluster"] = grid["cluster_raw"].map(remap)

    for cid in sorted(grid["cluster"].unique()):
        sub = grid[grid["cluster"] == cid]
        print(f"  Cluster {cid} — {LABEL_MAP[cid]}:")
        print(f"    squares              = {len(sub)}")
        print(f"    mean download (Mbps) = {sub['download_mbps_mean'].mean():.2f}")
        print(f"    mean latency  (ms)   = {sub['avg_latency_mean'].mean():.2f}")

    # ================================================================
    # Step 5 — Export artefacts
    # ================================================================
    # 5a. map_data.csv (frontend contract: lat, lng, cluster)
    map_df = grid[["lat", "lng", "cluster"]].copy()
    map_path = output_dir / "map_data.csv"
    map_df.to_csv(map_path, index=False)
    print(f"✓ {map_path}  ({len(map_df)} rows)")

    # 5b. Model artefacts
    joblib.dump(kmeans, model_dir / "clustering_model.pkl")
    joblib.dump(scaler, model_dir / "clustering_scaler.pkl")
    print(f"✓ clustering_model.pkl")
    print(f"✓ clustering_scaler.pkl")

    # Verification
    assert list(map_df.columns) == ["lat", "lng", "cluster"]
    assert set(map_df["cluster"].unique()) == {0, 1, 2}
    print(f"✓ Verification passed: {len(map_df)} rows, 3 clusters")


if __name__ == "__main__":
    main()


