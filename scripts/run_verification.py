"""
Full verification pipeline — runs clustering + forecasting and saves
all intermediate data, metrics, and plots into verification_output/.
Designed so that another Claude AI session can audit every step.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import (
    silhouette_score, silhouette_samples,
    davies_bouldin_score, calinski_harabasz_score,
    mean_squared_error, mean_absolute_error,
)
import os, pickle, json, warnings
warnings.filterwarnings("ignore")

BASE = os.path.join(os.path.dirname(__file__), "..")
VOUT = os.path.join(BASE, "verification_output")
C_OUT = os.path.join(VOUT, "clustering")
F_OUT = os.path.join(VOUT, "forecasting")
D_OUT = os.path.join(VOUT, "data_summary")
# Also keep outputs/ for Streamlit app
APP_OUT = os.path.join(BASE, "outputs")
for d in [VOUT, C_OUT, F_OUT, D_OUT, APP_OUT]:
    os.makedirs(d, exist_ok=True)

log_lines = []
def log(msg):
    print(msg)
    log_lines.append(msg)

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 0: DATA SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
log("=" * 70)
log("PHASE 0: DATA SUMMARY")
log("=" * 70)

clust_df = pd.read_csv(os.path.join(BASE, "data", "clustering_data.csv"))
ts_df = pd.read_csv(os.path.join(BASE, "data", "forecasting_data.csv"))

log(f"clustering_data.csv: {clust_df.shape[0]} rows x {clust_df.shape[1]} cols")
log(f"forecasting_data.csv: {ts_df.shape[0]} rows x {ts_df.shape[1]} cols")
log(f"Clustering columns: {list(clust_df.columns)}")
log(f"Forecasting columns: {list(ts_df.columns)}")
log(f"Clustering NaN count: {clust_df.isnull().sum().sum()}")
log(f"Forecasting NaN count: {ts_df.isnull().sum().sum()}")

# Save data summaries as CSV for auditing
clust_df.describe().round(4).to_csv(os.path.join(D_OUT, "clustering_data_describe.csv"))
ts_df.describe().round(4).to_csv(os.path.join(D_OUT, "forecasting_data_describe.csv"))
clust_df.head(20).to_csv(os.path.join(D_OUT, "clustering_data_head20.csv"), index=False)
ts_df.head(20).to_csv(os.path.join(D_OUT, "forecasting_data_head20.csv"), index=False)

log(f"\nClustering data stats:\n{clust_df.describe().round(2).to_string()}")
log(f"\nForecasting data stats:\n{ts_df.describe().round(2).to_string()}")

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: CLUSTERING
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("PHASE 1: CLUSTERING")
log("=" * 70)

# Step 1.1: Filter
df = clust_df.copy()
log(f"\n[1.1] Total zones before filtering: {len(df)}")
df = df[df["measurement_count"] >= 50].copy()
log(f"[1.1] Zones after filtering (measurement_count >= 50): {len(df)}")
log(f"[1.1] Zones removed: {len(clust_df) - len(df)}")

# Save filtered data
df.to_csv(os.path.join(C_OUT, "zones_filtered.csv"), index=False)

# Step 1.2: Feature selection
feature_cols = ["svr1", "upload_bitrate_mbps", "download_bitrate_mbps", "latitude", "longitude"]
log(f"\n[1.2] Clustering features: {feature_cols}")
X = df[feature_cols].values
log(f"[1.2] Feature matrix shape: {X.shape}")
log(f"[1.2] Feature ranges:")
for i, col in enumerate(feature_cols):
    log(f"       {col}: min={X[:, i].min():.4f}, max={X[:, i].max():.4f}, mean={X[:, i].mean():.4f}, std={X[:, i].std():.4f}")

# Step 1.3: Scaling
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
log(f"\n[1.3] StandardScaler applied. Post-scaling verification:")
for i, col in enumerate(feature_cols):
    log(f"       {col}: mean={X_scaled[:, i].mean():.6f}, std={X_scaled[:, i].std():.6f}")

# Save scaler
with open(os.path.join(APP_OUT, "scaler.pkl"), "wb") as f:
    pickle.dump(scaler, f)

# Step 1.4: Optimal K search
log(f"\n[1.4] Searching K=2..10")
K_range = range(2, 11)
k_results = []

for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)
    inertia = km.inertia_
    sil = silhouette_score(X_scaled, labels)
    db = davies_bouldin_score(X_scaled, labels)
    ch = calinski_harabasz_score(X_scaled, labels)
    sizes = [int(np.sum(labels == c)) for c in range(k)]
    k_results.append({
        "K": k, "inertia": round(inertia, 2), "silhouette": round(sil, 4),
        "davies_bouldin": round(db, 4), "calinski_harabasz": round(ch, 2),
        "cluster_sizes": sizes
    })
    log(f"       K={k}: silhouette={sil:.4f}, DB={db:.4f}, CH={ch:.2f}, sizes={sizes}")

k_results_df = pd.DataFrame(k_results)
k_results_df.to_csv(os.path.join(C_OUT, "k_selection_metrics.csv"), index=False)

best_k = k_results_df.loc[k_results_df["silhouette"].idxmax(), "K"]
log(f"\n[1.4] Best K by silhouette: {best_k}")

# Elbow + Silhouette plot
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].plot(k_results_df["K"], k_results_df["inertia"], "bo-")
axes[0].set_xlabel("K"); axes[0].set_ylabel("Inertia"); axes[0].set_title("Elbow Method")
axes[0].set_xticks(list(K_range))
axes[1].plot(k_results_df["K"], k_results_df["silhouette"], "ro-")
axes[1].set_xlabel("K"); axes[1].set_ylabel("Silhouette Score"); axes[1].set_title("Silhouette Score vs K")
axes[1].set_xticks(list(K_range))
plt.tight_layout()
plt.savefig(os.path.join(C_OUT, "elbow_silhouette.png"), dpi=150)
plt.savefig(os.path.join(APP_OUT, "elbow_silhouette.png"), dpi=150)
plt.close()

# Step 1.5: Final K-Means
log(f"\n[1.5] Running K-Means with K={best_k}")
kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
df["kmeans_cluster"] = kmeans.fit_predict(X_scaled)

with open(os.path.join(APP_OUT, "kmeans_model.pkl"), "wb") as f:
    pickle.dump(kmeans, f)

# Step 1.6: DBSCAN
log(f"\n[1.6] DBSCAN parameter search")
dbscan_results = []
best_db_score = -1
best_eps, best_ms = 0.5, 5

for eps in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]:
    for ms in [3, 5, 7, 10]:
        db = DBSCAN(eps=eps, min_samples=ms)
        labels = db.fit_predict(X_scaled)
        n_clusters = len(set(labels) - {-1})
        n_noise = int(np.sum(labels == -1))
        sil_val = None
        if n_clusters >= 2:
            mask = labels != -1
            if mask.sum() > 10:
                sil_val = silhouette_score(X_scaled[mask], labels[mask])
                if sil_val > best_db_score:
                    best_db_score = sil_val
                    best_eps, best_ms = eps, ms
        dbscan_results.append({
            "eps": eps, "min_samples": ms, "n_clusters": n_clusters,
            "n_noise": n_noise, "silhouette": round(sil_val, 4) if sil_val else None
        })

pd.DataFrame(dbscan_results).to_csv(os.path.join(C_OUT, "dbscan_parameter_search.csv"), index=False)

dbscan = DBSCAN(eps=best_eps, min_samples=best_ms)
df["dbscan_cluster"] = dbscan.fit_predict(X_scaled)
n_dbscan = len(set(df["dbscan_cluster"]) - {-1})
n_noise = int((df["dbscan_cluster"] == -1).sum())
log(f"[1.6] Best DBSCAN: eps={best_eps}, min_samples={best_ms}")
log(f"       Clusters: {n_dbscan}, Noise: {n_noise}")

# Step 1.7: Cluster profiles
log(f"\n[1.7] Cluster Profiles (K-Means)")
perf_cols = ["svr1", "upload_bitrate_mbps", "download_bitrate_mbps", "speed"]
profiles = df.groupby("kmeans_cluster")[perf_cols].agg(["mean", "std", "min", "max"])
profiles.columns = ["_".join(c) for c in profiles.columns]
profiles.to_csv(os.path.join(C_OUT, "cluster_profiles_detailed.csv"))
log(profiles.round(2).to_string())

# Simple profiles for naming
simple_profiles = df.groupby("kmeans_cluster")[["svr1", "upload_bitrate_mbps", "download_bitrate_mbps"]].mean()
cluster_names = {}
for c in range(best_k):
    p = simple_profiles.loc[c]
    lat_lbl = "High Latency" if p["svr1"] > df["svr1"].median() else "Low Latency"
    tp = p["upload_bitrate_mbps"] + p["download_bitrate_mbps"]
    med_tp = (df["upload_bitrate_mbps"] + df["download_bitrate_mbps"]).median()
    tp_lbl = "High Throughput" if tp > med_tp else "Low Throughput"
    cluster_names[c] = f"{lat_lbl} / {tp_lbl}"
    log(f"       Cluster {c}: {cluster_names[c]} (n={(df['kmeans_cluster']==c).sum()})")

# Step 1.8: Evaluation
sil_final = silhouette_score(X_scaled, df["kmeans_cluster"])
db_final = davies_bouldin_score(X_scaled, df["kmeans_cluster"])
ch_final = calinski_harabasz_score(X_scaled, df["kmeans_cluster"])

log(f"\n[1.8] Final K-Means Evaluation:")
log(f"       Silhouette Score:        {sil_final:.4f}")
log(f"       Davies-Bouldin Index:    {db_final:.4f}")
log(f"       Calinski-Harabasz Index: {ch_final:.2f}")

clustering_metrics = {
    "best_k": int(best_k),
    "silhouette": round(sil_final, 4),
    "davies_bouldin": round(db_final, 4),
    "calinski_harabasz": round(ch_final, 2),
    "cluster_names": cluster_names,
    "cluster_sizes": {int(c): int((df["kmeans_cluster"] == c).sum()) for c in range(best_k)},
    "feature_cols": feature_cols,
    "n_zones_total": len(clust_df),
    "n_zones_filtered": len(df),
    "dbscan_eps": best_eps,
    "dbscan_min_samples": best_ms,
    "dbscan_n_clusters": n_dbscan,
    "dbscan_n_noise": n_noise,
}
with open(os.path.join(C_OUT, "clustering_metrics.json"), "w") as f:
    json.dump(clustering_metrics, f, indent=2)

# Also save for app
meta = {
    "best_k": int(best_k), "feature_cols": feature_cols,
    "cluster_names": cluster_names, "silhouette": sil_final,
    "davies_bouldin": db_final, "calinski_harabasz": ch_final,
}
with open(os.path.join(APP_OUT, "clustering_meta.pkl"), "wb") as f:
    pickle.dump(meta, f)

# Step 1.9: Plots
# Map view
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
scatter1 = axes[0].scatter(df["longitude"], df["latitude"], c=df["kmeans_cluster"], cmap="tab10", s=30, alpha=0.7)
axes[0].set_xlabel("Longitude"); axes[0].set_ylabel("Latitude"); axes[0].set_title("K-Means Clusters (Map View)")
plt.colorbar(scatter1, ax=axes[0], label="Cluster")
scatter2 = axes[1].scatter(df["longitude"], df["latitude"], c=df["dbscan_cluster"], cmap="tab10", s=30, alpha=0.7)
axes[1].set_xlabel("Longitude"); axes[1].set_ylabel("Latitude"); axes[1].set_title("DBSCAN Clusters (Map View)")
plt.colorbar(scatter2, ax=axes[1], label="Cluster")
plt.tight_layout()
plt.savefig(os.path.join(C_OUT, "cluster_maps.png"), dpi=150)
plt.savefig(os.path.join(APP_OUT, "cluster_maps.png"), dpi=150)
plt.close()

# Feature bar chart
plot_feats = ["svr1", "upload_bitrate_mbps", "download_bitrate_mbps", "speed"]
cluster_means = df.groupby("kmeans_cluster")[plot_feats].mean()
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
for i, feat in enumerate(plot_feats):
    ax = axes[i // 2, i % 2]
    cluster_means[feat].plot(kind="bar", ax=ax, color=plt.cm.tab10(np.arange(best_k)))
    ax.set_title(feat); ax.set_xlabel("Cluster"); ax.set_ylabel("Mean Value")
plt.suptitle("Mean Feature Values per Cluster", fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(C_OUT, "cluster_profiles.png"), dpi=150, bbox_inches="tight")
plt.savefig(os.path.join(APP_OUT, "cluster_profiles.png"), dpi=150, bbox_inches="tight")
plt.close()

# Silhouette plot
sample_sil = silhouette_samples(X_scaled, df["kmeans_cluster"])
fig, ax = plt.subplots(figsize=(10, 6))
y_lower = 10
for i in range(best_k):
    vals = sample_sil[df["kmeans_cluster"] == i]
    vals.sort()
    y_upper = y_lower + len(vals)
    ax.fill_betweenx(np.arange(y_lower, y_upper), 0, vals, alpha=0.7, label=f"Cluster {i}")
    y_lower = y_upper + 10
ax.axvline(x=sil_final, color="red", linestyle="--", label=f"Avg: {sil_final:.3f}")
ax.set_xlabel("Silhouette Coefficient"); ax.set_ylabel("Cluster"); ax.set_title("Silhouette Plot (K-Means)")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(C_OUT, "silhouette_plot.png"), dpi=150)
plt.savefig(os.path.join(APP_OUT, "silhouette_plot.png"), dpi=150)
plt.close()

# Per-cluster silhouette scores
per_cluster_sil = []
for c in range(best_k):
    vals = sample_sil[df["kmeans_cluster"] == c]
    per_cluster_sil.append({
        "cluster": c, "name": cluster_names[c], "size": len(vals),
        "mean_silhouette": round(float(vals.mean()), 4),
        "min_silhouette": round(float(vals.min()), 4),
        "max_silhouette": round(float(vals.max()), 4),
        "pct_negative": round(float((vals < 0).mean() * 100), 1),
    })
pd.DataFrame(per_cluster_sil).to_csv(os.path.join(C_OUT, "per_cluster_silhouette.csv"), index=False)
log(f"\n[1.9] Per-cluster silhouette:")
for r in per_cluster_sil:
    log(f"       Cluster {r['cluster']} ({r['name']}): mean={r['mean_silhouette']}, negative={r['pct_negative']}%")

# Save clustered zones
df.to_csv(os.path.join(C_OUT, "zones_clustered.csv"), index=False)
df.to_csv(os.path.join(APP_OUT, "zones_clustered.csv"), index=False)

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: FORECASTING
# ═══════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("PHASE 2: FORECASTING")
log("=" * 70)

ts = ts_df.copy()
ts["datetime_hour"] = pd.to_datetime(ts["datetime_hour"])
ts["date"] = pd.to_datetime(ts["date"])

# Step 2.1: Merge cluster labels
cluster_map = df[["square_id", "kmeans_cluster"]].copy()
ts = ts.merge(cluster_map, on="square_id", how="inner")
log(f"\n[2.1] Time-series rows after merge: {len(ts)} (from {len(ts_df)})")
log(f"[2.1] Zones dropped (not in clustering): {ts_df['square_id'].nunique() - ts['square_id'].nunique()}")

# Step 2.2: Aggregate per cluster per hour
cluster_ts = ts.groupby(["kmeans_cluster", "datetime_hour"]).agg(
    svr1=("svr1", "mean"),
    upload_bitrate_mbps=("upload_bitrate_mbps", "mean"),
    download_bitrate_mbps=("download_bitrate_mbps", "mean"),
    target_latency=("target_latency", "mean"),
    target_throughput=("target_throughput", "mean"),
    latency_lag_1h=("latency_lag_1h", "mean"),
    throughput_lag_1h=("throughput_lag_1h", "mean"),
    latency_rolling_3h=("latency_rolling_3h", "mean"),
    throughput_rolling_3h=("throughput_rolling_3h", "mean"),
    latency_rolling_6h=("latency_rolling_6h", "mean"),
    throughput_rolling_6h=("throughput_rolling_6h", "mean"),
    hour_sin=("hour_sin", "first"),
    hour_cos=("hour_cos", "first"),
    dow_sin=("dow_sin", "first"),
    dow_cos=("dow_cos", "first"),
    hour_of_day=("hour_of_day", "first"),
    day_of_week=("day_of_week", "first"),
).reset_index()
cluster_ts = cluster_ts.sort_values(["kmeans_cluster", "datetime_hour"])

log(f"\n[2.2] Cluster-level hourly records: {len(cluster_ts)}")
for c in sorted(cluster_ts["kmeans_cluster"].unique()):
    n = (cluster_ts["kmeans_cluster"] == c).sum()
    log(f"       Cluster {c}: {n} hourly records")

cluster_ts.to_csv(os.path.join(F_OUT, "cluster_timeseries_aggregated.csv"), index=False)

# Step 2.3: Temporal train/test split
train_end = pd.Timestamp("2022-07-18")
test_start = pd.Timestamp("2022-07-19")

train = cluster_ts[cluster_ts["datetime_hour"] <= train_end].copy()
test = cluster_ts[cluster_ts["datetime_hour"] >= test_start].copy()

log(f"\n[2.3] Temporal split:")
log(f"       Train: {len(train)} rows ({train['datetime_hour'].min()} to {train['datetime_hour'].max()})")
log(f"       Test:  {len(test)} rows ({test['datetime_hour'].min()} to {test['datetime_hour'].max()})")

train.to_csv(os.path.join(F_OUT, "train_set_pre_winsorize.csv"), index=False)
test.to_csv(os.path.join(F_OUT, "test_set_pre_winsorize.csv"), index=False)

# Step 2.4: Winsorization (99th percentile capping)
log(f"\n[2.4] Winsorization (99th percentile capping)")
PERCENTILE = 0.99

# Compute caps from TRAINING DATA ONLY
latency_cap = train["target_latency"].quantile(PERCENTILE)
throughput_cap = train["target_throughput"].quantile(PERCENTILE)
log(f"       Latency cap (99th pct of train):    {latency_cap:.2f} ms")
log(f"       Throughput cap (99th pct of train):  {throughput_cap:.2f} Mbps")

# Columns to cap
latency_cols = [
    "svr1", "target_latency",
    "latency_lag_1h", "latency_rolling_3h", "latency_rolling_6h",
]
throughput_cols = [
    "upload_bitrate_mbps", "download_bitrate_mbps", "target_throughput",
    "throughput_lag_1h", "throughput_rolling_3h", "throughput_rolling_6h",
]

# Save pre-winsorization stats for comparison
pre_winsorize_stats = []

# Log and apply clipping
log(f"\n       Clipping latency columns (cap={latency_cap:.2f}):")
for col in latency_cols:
    if col in train.columns:
        n_train_clipped = int((train[col] > latency_cap).sum())
        n_test_clipped = int((test[col] > latency_cap).sum())
        orig_train_max = float(train[col].max())
        orig_test_max = float(test[col].max())
        train[col] = train[col].clip(upper=latency_cap)
        test[col] = test[col].clip(upper=latency_cap)
        pre_winsorize_stats.append({
            "column": col, "cap_type": "latency", "cap_value": round(latency_cap, 2),
            "train_clipped": n_train_clipped, "train_clipped_pct": round(n_train_clipped / len(train) * 100, 2),
            "test_clipped": n_test_clipped, "test_clipped_pct": round(n_test_clipped / len(test) * 100, 2),
            "train_max_before": round(orig_train_max, 2), "train_max_after": round(float(train[col].max()), 2),
            "test_max_before": round(orig_test_max, 2), "test_max_after": round(float(test[col].max()), 2),
        })
        if n_train_clipped > 0 or n_test_clipped > 0:
            log(f"         {col}: train={n_train_clipped} clipped ({n_train_clipped/len(train)*100:.1f}%), "
                f"test={n_test_clipped} clipped ({n_test_clipped/len(test)*100:.1f}%), "
                f"max: {orig_train_max:.1f} -> {latency_cap:.1f}")
        else:
            log(f"         {col}: no values clipped")

log(f"\n       Clipping throughput columns (cap={throughput_cap:.2f}):")
for col in throughput_cols:
    if col in train.columns:
        n_train_clipped = int((train[col] > throughput_cap).sum())
        n_test_clipped = int((test[col] > throughput_cap).sum())
        orig_train_max = float(train[col].max())
        orig_test_max = float(test[col].max())
        train[col] = train[col].clip(upper=throughput_cap)
        test[col] = test[col].clip(upper=throughput_cap)
        pre_winsorize_stats.append({
            "column": col, "cap_type": "throughput", "cap_value": round(throughput_cap, 2),
            "train_clipped": n_train_clipped, "train_clipped_pct": round(n_train_clipped / len(train) * 100, 2),
            "test_clipped": n_test_clipped, "test_clipped_pct": round(n_test_clipped / len(test) * 100, 2),
            "train_max_before": round(orig_train_max, 2), "train_max_after": round(float(train[col].max()), 2),
            "test_max_before": round(orig_test_max, 2), "test_max_after": round(float(test[col].max()), 2),
        })
        if n_train_clipped > 0 or n_test_clipped > 0:
            log(f"         {col}: train={n_train_clipped} clipped ({n_train_clipped/len(train)*100:.1f}%), "
                f"test={n_test_clipped} clipped ({n_test_clipped/len(test)*100:.1f}%), "
                f"max: {orig_train_max:.1f} -> {throughput_cap:.1f}")
        else:
            log(f"         {col}: no values clipped")

# Save winsorization summary
winsorize_df = pd.DataFrame(pre_winsorize_stats)
winsorize_df.to_csv(os.path.join(F_OUT, "winsorization_summary.csv"), index=False)
log(f"\n       Winsorization summary saved to forecasting/winsorization_summary.csv")

# Also build the winsorized cluster_ts for LSTM (which uses the full sorted series)
# Re-apply caps to cluster_ts as well
for col in latency_cols:
    if col in cluster_ts.columns:
        cluster_ts[col] = cluster_ts[col].clip(upper=latency_cap)
for col in throughput_cols:
    if col in cluster_ts.columns:
        cluster_ts[col] = cluster_ts[col].clip(upper=throughput_cap)

# Save post-winsorization data
train.to_csv(os.path.join(F_OUT, "train_set.csv"), index=False)
test.to_csv(os.path.join(F_OUT, "test_set.csv"), index=False)
cluster_ts.to_csv(os.path.join(F_OUT, "cluster_timeseries_winsorized.csv"), index=False)

# ── ARIMA ────────────────────────────────────────────────────────────────────
log(f"\n[2.5] ARIMA Forecasting")
from pmdarima import auto_arima

targets = ["target_latency", "target_throughput"]
arima_results = {}
arima_all_metrics = []

for target in targets:
    log(f"\n  --- {target} ---")
    for cluster_id in sorted(cluster_ts["kmeans_cluster"].unique()):
        c_train = train[train["kmeans_cluster"] == cluster_id][target].values
        c_test = test[test["kmeans_cluster"] == cluster_id][target].values

        if len(c_train) < 10 or len(c_test) < 2:
            log(f"  Cluster {cluster_id}: SKIP (train={len(c_train)}, test={len(c_test)})")
            continue

        try:
            model = auto_arima(c_train, seasonal=False, stepwise=True,
                               suppress_warnings=True, error_action="ignore",
                               max_p=5, max_q=5, max_d=2)
            preds = model.predict(n_periods=len(c_test))

            rmse = float(np.sqrt(mean_squared_error(c_test, preds)))
            mae = float(mean_absolute_error(c_test, preds))
            nonzero = c_test != 0
            mape = float(np.mean(np.abs((c_test[nonzero] - preds[nonzero]) / c_test[nonzero])) * 100) if nonzero.any() else float("nan")

            arima_results[(target, cluster_id)] = {
                "preds": preds, "actual": c_test,
                "rmse": rmse, "mae": mae, "mape": mape,
                "train_size": len(c_train), "test_size": len(c_test),
                "order": str(model.order),
            }

            arima_all_metrics.append({
                "target": target, "cluster": int(cluster_id), "model": "ARIMA",
                "order": str(model.order),
                "rmse": round(rmse, 4), "mae": round(mae, 4), "mape": round(mape, 2),
                "train_size": len(c_train), "test_size": len(c_test),
            })

            # Save predictions CSV
            pred_df = pd.DataFrame({"actual": c_test, "predicted": preds})
            pred_df.to_csv(os.path.join(F_OUT, f"arima_{target}_cluster{cluster_id}_predictions.csv"), index=False)

            log(f"  Cluster {cluster_id}: order={model.order}, RMSE={rmse:.2f}, MAE={mae:.2f}, MAPE={mape:.1f}%")

        except Exception as e:
            log(f"  Cluster {cluster_id}: ARIMA FAILED — {e}")

# Save ARIMA results for app
with open(os.path.join(APP_OUT, "arima_results.pkl"), "wb") as f:
    arima_save = {k: {kk: vv for kk, vv in v.items() if kk != "model"} for k, v in arima_results.items()}
    pickle.dump(arima_save, f)

# ── LSTM ─────────────────────────────────────────────────────────────────────
log(f"\n[2.6] LSTM Forecasting")

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
tf.random.set_seed(42)
np.random.seed(42)

WINDOW_SIZE = 6
lstm_results = {}
lstm_all_metrics = []

lstm_feature_map = {
    "target_latency": [
        "svr1", "latency_lag_1h", "latency_rolling_3h", "latency_rolling_6h",
        "hour_sin", "hour_cos", "dow_sin", "dow_cos"
    ],
    "target_throughput": [
        "upload_bitrate_mbps", "download_bitrate_mbps",
        "throughput_lag_1h", "throughput_rolling_3h", "throughput_rolling_6h",
        "hour_sin", "hour_cos", "dow_sin", "dow_cos"
    ],
}

for target in targets:
    log(f"\n  --- {target} ---")
    features = lstm_feature_map[target]

    for cluster_id in sorted(cluster_ts["kmeans_cluster"].unique()):
        c_data = cluster_ts[cluster_ts["kmeans_cluster"] == cluster_id].copy()
        c_data = c_data.sort_values("datetime_hour").reset_index(drop=True)

        all_cols = features + [target]
        data_arr = c_data[all_cols].values

        if len(data_arr) < WINDOW_SIZE + 5:
            log(f"  Cluster {cluster_id}: SKIP (only {len(data_arr)} records)")
            continue

        scaler_lstm = MinMaxScaler()
        data_scaled = scaler_lstm.fit_transform(data_arr)

        target_idx = len(all_cols) - 1
        X_seq, y_seq = [], []
        for i in range(len(data_scaled) - WINDOW_SIZE):
            X_seq.append(data_scaled[i:i + WINDOW_SIZE])
            y_seq.append(data_scaled[i + WINDOW_SIZE, target_idx])
        X_seq = np.array(X_seq)
        y_seq = np.array(y_seq)

        split_idx = int(len(X_seq) * 0.8)
        if split_idx < 3 or (len(X_seq) - split_idx) < 2:
            log(f"  Cluster {cluster_id}: SKIP (insufficient after windowing)")
            continue

        X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
        y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]

        log(f"  Cluster {cluster_id}: features={features}")
        log(f"       window={WINDOW_SIZE}, sequences={len(X_seq)}, train={len(X_train)}, test={len(X_test)}")

        model = Sequential([
            LSTM(32, input_shape=(WINDOW_SIZE, len(all_cols)), return_sequences=True),
            Dropout(0.2),
            LSTM(16),
            Dropout(0.2),
            Dense(1)
        ])
        model.compile(optimizer="adam", loss="mse")

        early_stop = EarlyStopping(patience=10, restore_best_weights=True, verbose=0)
        history = model.fit(X_train, y_train, epochs=100, batch_size=16,
                            validation_split=0.2, callbacks=[early_stop], verbose=0)

        epochs_trained = len(history.history["loss"])
        final_train_loss = history.history["loss"][-1]
        final_val_loss = history.history["val_loss"][-1]

        preds_scaled = model.predict(X_test, verbose=0).flatten()

        dummy = np.zeros((len(preds_scaled), len(all_cols)))
        dummy[:, target_idx] = preds_scaled
        preds_inv = scaler_lstm.inverse_transform(dummy)[:, target_idx]

        dummy_actual = np.zeros((len(y_test), len(all_cols)))
        dummy_actual[:, target_idx] = y_test
        actual_inv = scaler_lstm.inverse_transform(dummy_actual)[:, target_idx]

        rmse = float(np.sqrt(mean_squared_error(actual_inv, preds_inv)))
        mae = float(mean_absolute_error(actual_inv, preds_inv))
        nonzero = actual_inv != 0
        mape = float(np.mean(np.abs((actual_inv[nonzero] - preds_inv[nonzero]) / actual_inv[nonzero])) * 100) if nonzero.any() else float("nan")

        lstm_results[(target, cluster_id)] = {
            "preds": preds_inv, "actual": actual_inv,
            "rmse": rmse, "mae": mae, "mape": mape,
        }

        lstm_all_metrics.append({
            "target": target, "cluster": int(cluster_id), "model": "LSTM",
            "rmse": round(rmse, 4), "mae": round(mae, 4), "mape": round(mape, 2),
            "window_size": WINDOW_SIZE, "epochs_trained": epochs_trained,
            "final_train_loss": round(float(final_train_loss), 6),
            "final_val_loss": round(float(final_val_loss), 6),
            "train_sequences": len(X_train), "test_sequences": len(X_test),
            "features": str(features),
        })

        # Save predictions
        pred_df = pd.DataFrame({"actual": actual_inv, "predicted": preds_inv})
        pred_df.to_csv(os.path.join(F_OUT, f"lstm_{target}_cluster{cluster_id}_predictions.csv"), index=False)

        # Save training history
        hist_df = pd.DataFrame({"epoch": range(1, epochs_trained + 1),
                                 "train_loss": history.history["loss"],
                                 "val_loss": history.history["val_loss"]})
        hist_df.to_csv(os.path.join(F_OUT, f"lstm_{target}_cluster{cluster_id}_training_history.csv"), index=False)

        model.save(os.path.join(APP_OUT, f"lstm_{target}_cluster{cluster_id}.keras"))

        log(f"       epochs={epochs_trained}, train_loss={final_train_loss:.6f}, val_loss={final_val_loss:.6f}")
        log(f"       RMSE={rmse:.2f}, MAE={mae:.2f}, MAPE={mape:.1f}%")

with open(os.path.join(APP_OUT, "lstm_results.pkl"), "wb") as f:
    pickle.dump(lstm_results, f)

# Save all forecasting metrics
all_metrics = arima_all_metrics + lstm_all_metrics
pd.DataFrame(all_metrics).to_csv(os.path.join(F_OUT, "all_forecasting_metrics.csv"), index=False)

# ── Forecast plots ───────────────────────────────────────────────────────────
log(f"\n[2.7] Generating forecast plots")

for target in targets:
    arima_clusters = [c for (t, c) in arima_results if t == target]
    lstm_clusters = [c for (t, c) in lstm_results if t == target]
    all_clusters = sorted(set(arima_clusters) | set(lstm_clusters))
    if not all_clusters:
        continue

    fig, axes = plt.subplots(len(all_clusters), 1, figsize=(14, 5 * len(all_clusters)))
    if len(all_clusters) == 1:
        axes = [axes]

    for i, cid in enumerate(all_clusters):
        ax = axes[i]
        if (target, cid) in arima_results:
            r = arima_results[(target, cid)]
            ax.plot(r["actual"], "b-o", label="Actual", markersize=3)
            ax.plot(r["preds"], "r--s", label=f"ARIMA (RMSE={r['rmse']:.2f})", markersize=3)
        if (target, cid) in lstm_results:
            r = lstm_results[(target, cid)]
            ax.plot(range(len(r["actual"])), r["actual"], "b-o", label="Actual (LSTM)", markersize=3, alpha=0.5)
            ax.plot(range(len(r["preds"])), r["preds"], "g--^", label=f"LSTM (RMSE={r['rmse']:.2f})", markersize=3)
        ax.set_title(f"Cluster {cid} — {target}")
        ax.set_xlabel("Time Step"); ax.set_ylabel(target); ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(F_OUT, f"forecast_{target}.png"), dpi=150, bbox_inches="tight")
    plt.savefig(os.path.join(APP_OUT, f"forecast_{target}.png"), dpi=150, bbox_inches="tight")
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════
# SAVE FULL LOG
# ═══════════════════════════════════════════════════════════════════════════
with open(os.path.join(VOUT, "full_run_log.txt"), "w") as f:
    f.write("\n".join(log_lines))

log(f"\n{'=' * 70}")
log("ALL DONE — verification outputs saved to verification_output/")
log(f"{'=' * 70}")
