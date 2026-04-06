"""
SageMaker Training Job — K-Means Clustering (Spatial Quality Labels).

Replicates the full pipeline from Notebook 2 (2_model_clustering.ipynb):
  1. Load cleaned_5g_data.csv
  2. Reconstruct base features dropped by feature-selection
  3. Aggregate per square_id (5 core network-quality features)
  4. Winsorise P5/P95 → log1p → RobustScaler → PCA auto-select (2 or 3)
  5. K-Means (k=3, n_init=50) + deterministic quality relabelling
  6. Export map_data.csv + model artefacts

Frontend contract: backend/data/map_data.csv with columns lat, lng, cluster (∈ {0,1,2}).
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import RobustScaler

# 5 core features — removed 4 correlated/redundant ones from the original 9
CLUSTER_FEATURES = [
    "download_mbps_mean",
    "avg_latency_mean",
    "cwnd_mean",
    "retransmission_rate_mean",
    "jitter_mean",
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
    # Step 4 — Winsorise + log1p + RobustScaler + PCA + K-Means
    # ================================================================
    X_pre = grid[CLUSTER_FEATURES].fillna(0).copy()

    # Winsorise at P5 / P95
    for col in X_pre.columns:
        lo, hi = np.percentile(X_pre[col], [5, 95])
        X_pre[col] = np.clip(X_pre[col], lo, hi)

    # Log1p on right-skewed features
    for col in ["retransmission_rate_mean", "jitter_mean"]:
        if (X_pre[col] >= 0).all():
            X_pre[col] = np.log1p(X_pre[col])

    # RobustScaler (median / IQR based)
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X_pre)

    # PCA: auto-select best dimensionality (2 or 3) by silhouette
    print("PCA dimensionality search:")
    best_sil_pca, N_COMPONENTS = -1, 2
    for n_try in [2, 3]:
        _pca = PCA(n_components=n_try, random_state=42)
        _X = _pca.fit_transform(X_scaled)
        _km = KMeans(n_clusters=3, random_state=42, n_init=50)
        _s = silhouette_score(_X, _km.fit_predict(_X))
        var_pct = _pca.explained_variance_ratio_.sum()
        print(f"  PCA({n_try}): silhouette = {_s:.3f}  variance = {var_pct:.1%}")
        if _s > best_sil_pca:
            best_sil_pca, N_COMPONENTS = _s, n_try

    pca = PCA(n_components=N_COMPONENTS, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    print(f"→ Selected PCA({N_COMPONENTS})  (best silhouette = {best_sil_pca:.3f})")

    # K-Means
    kmeans = KMeans(n_clusters=args.n_clusters, random_state=42, n_init=50)
    grid["cluster_raw"] = kmeans.fit_predict(X_pca)
    sil_score = silhouette_score(X_pca, grid["cluster_raw"])
    print(f"Silhouette score: {sil_score:.3f}")

    # Deterministic re-labelling: 0=Poor, 1=Medium, 2=Good
    centroid_profiles = grid.groupby("cluster_raw")[["download_mbps_mean", "avg_latency_mean"]].mean()
    centroid_profiles["_quality_score"] = (
        centroid_profiles["download_mbps_mean"] - centroid_profiles["avg_latency_mean"]
    )
    sorted_labels = centroid_profiles["_quality_score"].sort_values().index.tolist()
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
    joblib.dump(pca,    model_dir / "clustering_pca.pkl")

    config = {
        "cluster_features": CLUSTER_FEATURES,
        "n_pca_components": N_COMPONENTS,
        "scaler_type": "RobustScaler",
        "winsorise_limits": [0.05, 0.05],
        "log_transform_features": ["retransmission_rate_mean", "jitter_mean"],
        "silhouette_score": round(sil_score, 4),
    }
    (model_dir / "clustering_config.json").write_text(json.dumps(config, indent=2))

    print(f"✓ clustering_model.pkl")
    print(f"✓ clustering_scaler.pkl")
    print(f"✓ clustering_pca.pkl")
    print(f"✓ clustering_config.json")

    # Verification
    assert list(map_df.columns) == ["lat", "lng", "cluster"]
    assert set(map_df["cluster"].unique()) == {0, 1, 2}
    print(f"✓ Verification passed: {len(map_df)} rows, 3 clusters")


if __name__ == "__main__":
    main()


