"""
Task 1: Clustering — Zone Grouping based on 5G Network Performance
K-Means and DBSCAN on clustering_data.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score, silhouette_samples, davies_bouldin_score, calinski_harabasz_score
import os
import pickle

PROJECT_DIR = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 1. Load and filter ──────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(PROJECT_DIR, "data", "clustering_data.csv"))
print(f"Total zones: {len(df)}")

# Filter out zones with fewer than 50 measurements (unreliable)
df = df[df["measurement_count"] >= 50].copy()
print(f"Zones after filtering (measurement_count >= 50): {len(df)}")

# ── 2. Select features ──────────────────────────────────────────────────────
# Network performance features + geographic location
feature_cols = [
    "svr1",                    # server latency
    "upload_bitrate_mbps",     # upload speed
    "download_bitrate_mbps",   # download speed
    "latitude", "longitude"
]

X = df[feature_cols].values

# ── 3. Scale features ───────────────────────────────────────────────────────
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Save scaler for UI
with open(os.path.join(OUTPUT_DIR, "scaler.pkl"), "wb") as f:
    pickle.dump(scaler, f)

# ── 4. Determine optimal K (Elbow + Silhouette) ─────────────────────────────
K_range = range(2, 11)
inertias = []
silhouettes = []

for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)
    inertias.append(km.inertia_)
    silhouettes.append(silhouette_score(X_scaled, labels))

# Plot Elbow
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].plot(K_range, inertias, "bo-")
axes[0].set_xlabel("Number of Clusters (K)")
axes[0].set_ylabel("Inertia")
axes[0].set_title("Elbow Method")
axes[0].set_xticks(list(K_range))

# Plot Silhouette
axes[1].plot(K_range, silhouettes, "ro-")
axes[1].set_xlabel("Number of Clusters (K)")
axes[1].set_ylabel("Silhouette Score")
axes[1].set_title("Silhouette Score vs K")
axes[1].set_xticks(list(K_range))

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "elbow_silhouette.png"), dpi=150)
plt.close()

# Pick best K based on silhouette
best_k = list(K_range)[np.argmax(silhouettes)]
print(f"\nBest K by silhouette: {best_k} (score={max(silhouettes):.4f})")

# ── 5. Run K-Means with best K ──────────────────────────────────────────────
kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
df["kmeans_cluster"] = kmeans.fit_predict(X_scaled)

# Save model
with open(os.path.join(OUTPUT_DIR, "kmeans_model.pkl"), "wb") as f:
    pickle.dump(kmeans, f)

# ── 6. Run DBSCAN ───────────────────────────────────────────────────────────
best_db_score = -1
best_eps = 0.5
best_min_samples = 5

for eps in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]:
    for ms in [3, 5, 7, 10]:
        db = DBSCAN(eps=eps, min_samples=ms)
        labels = db.fit_predict(X_scaled)
        n_clusters = len(set(labels) - {-1})
        if n_clusters >= 2:
            mask = labels != -1
            if mask.sum() > 10:
                score = silhouette_score(X_scaled[mask], labels[mask])
                if score > best_db_score:
                    best_db_score = score
                    best_eps = eps
                    best_min_samples = ms

dbscan = DBSCAN(eps=best_eps, min_samples=best_min_samples)
df["dbscan_cluster"] = dbscan.fit_predict(X_scaled)
n_dbscan_clusters = len(set(df["dbscan_cluster"]) - {-1})
n_noise = (df["dbscan_cluster"] == -1).sum()
print(f"\nDBSCAN (eps={best_eps}, min_samples={best_min_samples}):")
print(f"  Clusters: {n_dbscan_clusters}, Noise points: {n_noise}")

if n_dbscan_clusters >= 2:
    mask = df["dbscan_cluster"] != -1
    db_sil = silhouette_score(X_scaled[mask], df.loc[mask, "dbscan_cluster"])
    print(f"  Silhouette (excl. noise): {db_sil:.4f}")

# ── 7. Label clusters meaningfully ──────────────────────────────────────────
perf_cols = ["svr1", "upload_bitrate_mbps", "download_bitrate_mbps"]
print("\n=== K-Means Cluster Profiles ===")
cluster_profiles = df.groupby("kmeans_cluster")[perf_cols].mean()
print(cluster_profiles.round(2).to_string())

# Generate descriptive names based on latency and throughput
cluster_names = {}
for c in range(best_k):
    profile = cluster_profiles.loc[c]
    lat_level = "High Latency" if profile["svr1"] > df["svr1"].median() else "Low Latency"
    total_tp = profile["upload_bitrate_mbps"] + profile["download_bitrate_mbps"]
    median_tp = (df["upload_bitrate_mbps"] + df["download_bitrate_mbps"]).median()
    tp_level = "High Throughput" if total_tp > median_tp else "Low Throughput"
    cluster_names[c] = f"{lat_level} / {tp_level}"

print("\nCluster Names:")
for c, name in cluster_names.items():
    size = (df["kmeans_cluster"] == c).sum()
    print(f"  Cluster {c}: {name} (n={size})")

# ── 8. Visualizations ───────────────────────────────────────────────────────

# 8a. Map view — lat/lon colored by cluster
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

scatter1 = axes[0].scatter(df["longitude"], df["latitude"],
                           c=df["kmeans_cluster"], cmap="tab10", s=30, alpha=0.7)
axes[0].set_xlabel("Longitude")
axes[0].set_ylabel("Latitude")
axes[0].set_title("K-Means Clusters (Map View)")
plt.colorbar(scatter1, ax=axes[0], label="Cluster")

colors = df["dbscan_cluster"].copy()
scatter2 = axes[1].scatter(df["longitude"], df["latitude"],
                           c=colors, cmap="tab10", s=30, alpha=0.7)
axes[1].set_xlabel("Longitude")
axes[1].set_ylabel("Latitude")
axes[1].set_title("DBSCAN Clusters (Map View)")
plt.colorbar(scatter2, ax=axes[1], label="Cluster")

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cluster_maps.png"), dpi=150)
plt.close()

# 8b. Bar chart — mean feature values per K-Means cluster
plot_features = ["svr1", "upload_bitrate_mbps", "download_bitrate_mbps", "speed"]
cluster_means = df.groupby("kmeans_cluster")[plot_features].mean()

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
for i, feat in enumerate(plot_features):
    ax = axes[i // 2, i % 2]
    cluster_means[feat].plot(kind="bar", ax=ax, color=plt.cm.tab10(np.arange(best_k)))
    ax.set_title(feat)
    ax.set_xlabel("Cluster")
    ax.set_ylabel("Mean Value")

plt.suptitle("Mean Feature Values per Cluster", fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cluster_profiles.png"), dpi=150, bbox_inches="tight")
plt.close()

# 8c. Silhouette plot per cluster
sample_silhouette_values = silhouette_samples(X_scaled, df["kmeans_cluster"])
fig, ax = plt.subplots(figsize=(10, 6))
y_lower = 10

for i in range(best_k):
    ith_cluster_values = sample_silhouette_values[df["kmeans_cluster"] == i]
    ith_cluster_values.sort()
    size_cluster_i = ith_cluster_values.shape[0]
    y_upper = y_lower + size_cluster_i

    ax.fill_betweenx(np.arange(y_lower, y_upper), 0, ith_cluster_values,
                     alpha=0.7, label=f"Cluster {i}")
    y_lower = y_upper + 10

avg_score = silhouette_score(X_scaled, df["kmeans_cluster"])
ax.axvline(x=avg_score, color="red", linestyle="--", label=f"Avg: {avg_score:.3f}")
ax.set_xlabel("Silhouette Coefficient")
ax.set_ylabel("Cluster")
ax.set_title("Silhouette Plot (K-Means)")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "silhouette_plot.png"), dpi=150)
plt.close()

# ── 9. Evaluation metrics ───────────────────────────────────────────────────
print("\n=== K-Means Evaluation ===")
sil = silhouette_score(X_scaled, df["kmeans_cluster"])
db_idx = davies_bouldin_score(X_scaled, df["kmeans_cluster"])
ch_idx = calinski_harabasz_score(X_scaled, df["kmeans_cluster"])
print(f"  Silhouette Score:       {sil:.4f}")
print(f"  Davies-Bouldin Index:   {db_idx:.4f}")
print(f"  Calinski-Harabasz Index: {ch_idx:.4f}")

print("\n  Cluster size distribution:")
for c in range(best_k):
    n = (df["kmeans_cluster"] == c).sum()
    print(f"    Cluster {c}: {n} zones ({100*n/len(df):.1f}%)")

# ── Save results ─────────────────────────────────────────────────────────────
df.to_csv(os.path.join(OUTPUT_DIR, "zones_clustered.csv"), index=False)

meta = {
    "best_k": best_k,
    "feature_cols": feature_cols,
    "cluster_names": cluster_names,
    "silhouette": sil,
    "davies_bouldin": db_idx,
    "calinski_harabasz": ch_idx,
}
with open(os.path.join(OUTPUT_DIR, "clustering_meta.pkl"), "wb") as f:
    pickle.dump(meta, f)

print(f"\nOutputs saved to {OUTPUT_DIR}/")
print("Done!")
