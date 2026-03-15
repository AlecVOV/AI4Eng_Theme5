"""
Task 2: Forecasting — Predict next-period 5G network performance
Cluster-based approach using pre-engineered features from forecasting_data.csv
Models: ARIMA + LSTM
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle
import os
import warnings
warnings.filterwarnings("ignore")

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

PROJECT_DIR = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "outputs")

# ── 1. Load data & merge cluster labels ──────────────────────────────────────
ts = pd.read_csv(os.path.join(PROJECT_DIR, "data", "forecasting_data.csv"))
zones = pd.read_csv(os.path.join(OUTPUT_DIR, "zones_clustered.csv"))

ts["datetime_hour"] = pd.to_datetime(ts["datetime_hour"])
ts["date"] = pd.to_datetime(ts["date"])

# Merge cluster labels
cluster_map = zones[["square_id", "kmeans_cluster"]].copy()
ts = ts.merge(cluster_map, on="square_id", how="inner")
print(f"Time-series rows after merge: {len(ts)}")
print(f"Clusters in data: {sorted(ts['kmeans_cluster'].unique())}")

# ── 2. Aggregate per cluster per hour ────────────────────────────────────────
# The new data has explicit target columns and lag/rolling features
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

print(f"\nCluster-level hourly records: {len(cluster_ts)}")
for c in sorted(cluster_ts["kmeans_cluster"].unique()):
    n = (cluster_ts["kmeans_cluster"] == c).sum()
    print(f"  Cluster {c}: {n} hourly records")

# ── 3. Train/test split — TEMPORAL ──────────────────────────────────────────
train_end = pd.Timestamp("2022-07-18")
test_start = pd.Timestamp("2022-07-19")

train = cluster_ts[cluster_ts["datetime_hour"] <= train_end].copy()
test = cluster_ts[cluster_ts["datetime_hour"] >= test_start].copy()

print(f"\nTrain: {len(train)} rows (up to {train_end.date()})")
print(f"Test:  {len(test)} rows (from {test_start.date()})")

# ── 4. Winsorization (99th percentile capping) ──────────────────────────────
print("\n" + "="*60)
print("WINSORIZATION (99th percentile)")
print("="*60)

PERCENTILE = 0.99
latency_cap = train["target_latency"].quantile(PERCENTILE)
throughput_cap = train["target_throughput"].quantile(PERCENTILE)
print(f"Latency cap (99th pct of train):   {latency_cap:.2f} ms")
print(f"Throughput cap (99th pct of train): {throughput_cap:.2f} Mbps")

latency_cols = ["svr1", "target_latency", "latency_lag_1h", "latency_rolling_3h", "latency_rolling_6h"]
throughput_cols = ["upload_bitrate_mbps", "download_bitrate_mbps", "target_throughput",
                   "throughput_lag_1h", "throughput_rolling_3h", "throughput_rolling_6h"]

for col in latency_cols:
    if col in train.columns:
        train[col] = train[col].clip(upper=latency_cap)
    if col in test.columns:
        test[col] = test[col].clip(upper=latency_cap)
for col in throughput_cols:
    if col in train.columns:
        train[col] = train[col].clip(upper=throughput_cap)
    if col in test.columns:
        test[col] = test[col].clip(upper=throughput_cap)

# Also cap cluster_ts for LSTM windowing
for col in latency_cols:
    if col in cluster_ts.columns:
        cluster_ts[col] = cluster_ts[col].clip(upper=latency_cap)
for col in throughput_cols:
    if col in cluster_ts.columns:
        cluster_ts[col] = cluster_ts[col].clip(upper=throughput_cap)

print("Winsorization applied to train, test, and cluster_ts.")

# ── ARIMA Forecasting ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("ARIMA FORECASTING")
print("="*60)

from pmdarima import auto_arima

arima_results = {}
targets = ["target_latency", "target_throughput"]

for target in targets:
    print(f"\n--- Target: {target} ---")
    for cluster_id in sorted(cluster_ts["kmeans_cluster"].unique()):
        c_train = train[train["kmeans_cluster"] == cluster_id][target].values
        c_test = test[test["kmeans_cluster"] == cluster_id][target].values

        if len(c_train) < 10 or len(c_test) < 2:
            print(f"  Cluster {cluster_id}: Insufficient data (train={len(c_train)}, test={len(c_test)}), skipping")
            continue

        try:
            model = auto_arima(c_train, seasonal=False, stepwise=True,
                               suppress_warnings=True, error_action="ignore",
                               max_p=5, max_q=5, max_d=2)
            preds = model.predict(n_periods=len(c_test))

            rmse = np.sqrt(mean_squared_error(c_test, preds))
            mae = mean_absolute_error(c_test, preds)
            nonzero = c_test != 0
            if nonzero.any():
                mape = np.mean(np.abs((c_test[nonzero] - preds[nonzero]) / c_test[nonzero])) * 100
            else:
                mape = float("nan")

            arima_results[(target, cluster_id)] = {
                "model": model, "preds": preds, "actual": c_test,
                "rmse": rmse, "mae": mae, "mape": mape,
                "train_size": len(c_train), "test_size": len(c_test)
            }
            print(f"  Cluster {cluster_id}: RMSE={rmse:.2f}, MAE={mae:.2f}, MAPE={mape:.1f}%")
        except Exception as e:
            print(f"  Cluster {cluster_id}: ARIMA failed — {e}")

# Save ARIMA results (without model objects)
with open(os.path.join(OUTPUT_DIR, "arima_results.pkl"), "wb") as f:
    arima_save = {}
    for k, v in arima_results.items():
        arima_save[k] = {kk: vv for kk, vv in v.items() if kk != "model"}
    pickle.dump(arima_save, f)

# ── LSTM Forecasting ────────────────────────────────────────────────────────
print("\n" + "="*60)
print("LSTM FORECASTING")
print("="*60)

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

tf.random.set_seed(42)
np.random.seed(42)

WINDOW_SIZE = 6
lstm_results = {}

# Feature sets for each target — leverage the pre-engineered lag/rolling features
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
    print(f"\n--- Target: {target} ---")
    features = lstm_feature_map[target]

    for cluster_id in sorted(cluster_ts["kmeans_cluster"].unique()):
        c_data = cluster_ts[cluster_ts["kmeans_cluster"] == cluster_id].copy()
        c_data = c_data.sort_values("datetime_hour").reset_index(drop=True)

        # Combine features + target into array
        all_cols = features + [target]
        data_arr = c_data[all_cols].values

        if len(data_arr) < WINDOW_SIZE + 5:
            print(f"  Cluster {cluster_id}: Too few records ({len(data_arr)}), skipping")
            continue

        # Normalize
        scaler_lstm = MinMaxScaler()
        data_scaled = scaler_lstm.fit_transform(data_arr)

        # Create sequences — target is the last column
        target_idx = len(all_cols) - 1
        X_seq, y_seq = [], []
        for i in range(len(data_scaled) - WINDOW_SIZE):
            X_seq.append(data_scaled[i:i + WINDOW_SIZE])
            y_seq.append(data_scaled[i + WINDOW_SIZE, target_idx])

        X_seq = np.array(X_seq)
        y_seq = np.array(y_seq)

        # Temporal split (80/20)
        split_idx = int(len(X_seq) * 0.8)
        if split_idx < 3 or (len(X_seq) - split_idx) < 2:
            print(f"  Cluster {cluster_id}: Insufficient after windowing, skipping")
            continue

        X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
        y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]

        # Build model
        model = Sequential([
            LSTM(32, input_shape=(WINDOW_SIZE, len(all_cols)), return_sequences=True),
            Dropout(0.2),
            LSTM(16),
            Dropout(0.2),
            Dense(1)
        ])
        model.compile(optimizer="adam", loss="mse")

        early_stop = EarlyStopping(patience=10, restore_best_weights=True, verbose=0)
        model.fit(X_train, y_train, epochs=100, batch_size=16,
                  validation_split=0.2, callbacks=[early_stop], verbose=0)

        # Predict
        preds_scaled = model.predict(X_test, verbose=0).flatten()

        # Inverse transform for target column
        dummy = np.zeros((len(preds_scaled), len(all_cols)))
        dummy[:, target_idx] = preds_scaled
        preds_inv = scaler_lstm.inverse_transform(dummy)[:, target_idx]

        dummy_actual = np.zeros((len(y_test), len(all_cols)))
        dummy_actual[:, target_idx] = y_test
        actual_inv = scaler_lstm.inverse_transform(dummy_actual)[:, target_idx]

        rmse = np.sqrt(mean_squared_error(actual_inv, preds_inv))
        mae = mean_absolute_error(actual_inv, preds_inv)
        nonzero = actual_inv != 0
        if nonzero.any():
            mape = np.mean(np.abs((actual_inv[nonzero] - preds_inv[nonzero]) / actual_inv[nonzero])) * 100
        else:
            mape = float("nan")

        lstm_results[(target, cluster_id)] = {
            "preds": preds_inv, "actual": actual_inv,
            "rmse": rmse, "mae": mae, "mape": mape,
        }
        print(f"  Cluster {cluster_id}: RMSE={rmse:.2f}, MAE={mae:.2f}, MAPE={mape:.1f}%")

        model.save(os.path.join(OUTPUT_DIR, f"lstm_{target}_cluster{cluster_id}.keras"))

# Save LSTM results
with open(os.path.join(OUTPUT_DIR, "lstm_results.pkl"), "wb") as f:
    pickle.dump(lstm_results, f)

# ── Visualization: Predicted vs Actual ───────────────────────────────────────
print("\n" + "="*60)
print("GENERATING PLOTS")
print("="*60)

for target in targets:
    arima_clusters = [c for (t, c) in arima_results if t == target]
    lstm_clusters = [c for (t, c) in lstm_results if t == target]
    all_clusters = sorted(set(arima_clusters) | set(lstm_clusters))

    if not all_clusters:
        continue

    fig, axes = plt.subplots(len(all_clusters), 1, figsize=(14, 5 * len(all_clusters)))
    if len(all_clusters) == 1:
        axes = [axes]

    for i, cluster_id in enumerate(all_clusters):
        ax = axes[i]

        if (target, cluster_id) in arima_results:
            r = arima_results[(target, cluster_id)]
            ax.plot(r["actual"], "b-o", label="Actual", markersize=3)
            ax.plot(r["preds"], "r--s", label=f"ARIMA (RMSE={r['rmse']:.2f})", markersize=3)

        if (target, cluster_id) in lstm_results:
            r = lstm_results[(target, cluster_id)]
            ax.plot(range(len(r["actual"])), r["actual"], "b-o", label="Actual (LSTM split)", markersize=3, alpha=0.5)
            ax.plot(range(len(r["preds"])), r["preds"], "g--^", label=f"LSTM (RMSE={r['rmse']:.2f})", markersize=3)

        ax.set_title(f"Cluster {cluster_id} — {target}")
        ax.set_xlabel("Time Step")
        ax.set_ylabel(target)
        ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"forecast_{target}.png"), dpi=150, bbox_inches="tight")
    plt.close()

# ── Summary comparison ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("MODEL COMPARISON SUMMARY")
print("="*60)
print(f"\n{'Target':<22} {'Cluster':<10} {'Model':<8} {'RMSE':<10} {'MAE':<10} {'MAPE%':<10}")
print("-" * 70)

for target in targets:
    for cluster_id in sorted(set(c for (_, c) in list(arima_results.keys()) + list(lstm_results.keys()))):
        if (target, cluster_id) in arima_results:
            r = arima_results[(target, cluster_id)]
            print(f"{target:<22} {cluster_id:<10} {'ARIMA':<8} {r['rmse']:<10.2f} {r['mae']:<10.2f} {r['mape']:<10.1f}")
        if (target, cluster_id) in lstm_results:
            r = lstm_results[(target, cluster_id)]
            print(f"{target:<22} {cluster_id:<10} {'LSTM':<8} {r['rmse']:<10.2f} {r['mae']:<10.2f} {r['mape']:<10.1f}")

print(f"\nAll outputs saved to {OUTPUT_DIR}/")
print("Done!")
