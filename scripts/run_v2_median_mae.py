"""
V2 Forecasting Pipeline: Median Aggregation + MAE Loss
- Clustering is UNCHANGED (reads existing zones_clustered.csv)
- Aggregation changed from mean -> median for targets/features
- LSTM loss changed from MSE -> MAE
- All outputs saved to verification_output/v2_median_mae/
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle
import json
import os
import warnings
warnings.filterwarnings("ignore")

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

BASE = os.path.join(os.path.dirname(__file__), "..")
V2_OUT = os.path.join(BASE, "verification_output", "v2_median_mae")
os.makedirs(V2_OUT, exist_ok=True)

LOG_PATH = os.path.join(V2_OUT, "full_run_log.txt")
log_file = open(LOG_PATH, "w", encoding="utf-8")

def log(msg):
    print(msg)
    log_file.write(msg + "\n")
    log_file.flush()

# ═════════════════════════════════════════════════════════════════════════════
# STEP 1: Load data
# ═════════════════════════════════════════════════════════════════════════════
log("=" * 70)
log("V2 PIPELINE: MEDIAN AGGREGATION + MAE LOSS")
log("=" * 70)

ts = pd.read_csv(os.path.join(BASE, "data", "forecasting_data.csv"))
zones = pd.read_csv(os.path.join(BASE, "verification_output", "clustering", "zones_clustered.csv"))

ts["datetime_hour"] = pd.to_datetime(ts["datetime_hour"])
ts["date"] = pd.to_datetime(ts["date"])

# Merge cluster labels
cluster_map = zones[["square_id", "kmeans_cluster"]].copy()
ts = ts.merge(cluster_map, on="square_id", how="inner")
log(f"\n[1] Time-series rows after merge: {len(ts)}")
log(f"    Clusters: {sorted(ts['kmeans_cluster'].unique())}")

# ═════════════════════════════════════════════════════════════════════════════
# STEP 2: MEDIAN aggregation per cluster per hour (PRIMARY CHANGE)
# ═════════════════════════════════════════════════════════════════════════════
log(f"\n[2] Aggregating per cluster per hour using MEDIAN")

cluster_ts = ts.groupby(["kmeans_cluster", "datetime_hour"]).agg(
    svr1=("svr1", "median"),
    upload_bitrate_mbps=("upload_bitrate_mbps", "median"),
    download_bitrate_mbps=("download_bitrate_mbps", "median"),
    target_latency=("target_latency", "median"),
    target_throughput=("target_throughput", "median"),
    latency_lag_1h=("latency_lag_1h", "median"),
    throughput_lag_1h=("throughput_lag_1h", "median"),
    latency_rolling_3h=("latency_rolling_3h", "median"),
    throughput_rolling_3h=("throughput_rolling_3h", "median"),
    latency_rolling_6h=("latency_rolling_6h", "median"),
    throughput_rolling_6h=("throughput_rolling_6h", "median"),
    hour_sin=("hour_sin", "first"),
    hour_cos=("hour_cos", "first"),
    dow_sin=("dow_sin", "first"),
    dow_cos=("dow_cos", "first"),
    hour_of_day=("hour_of_day", "first"),
    day_of_week=("day_of_week", "first"),
    zone_count=("square_id", "count"),
).reset_index()
cluster_ts = cluster_ts.sort_values(["kmeans_cluster", "datetime_hour"])

log(f"    Cluster-level hourly records: {len(cluster_ts)}")
for c in sorted(cluster_ts["kmeans_cluster"].unique()):
    n = (cluster_ts["kmeans_cluster"] == c).sum()
    log(f"    Cluster {c}: {n} hourly records")

cluster_ts.to_csv(os.path.join(V2_OUT, "cluster_timeseries_aggregated.csv"), index=False)

# Compare median vs mean aggregation stats
log(f"\n    Median vs Mean comparison (target_latency):")
mean_agg = ts.groupby(["kmeans_cluster", "datetime_hour"])["target_latency"].mean()
median_agg = ts.groupby(["kmeans_cluster", "datetime_hour"])["target_latency"].median()
log(f"    Mean agg:   std={mean_agg.std():.2f}, range=[{mean_agg.min():.1f}, {mean_agg.max():.1f}]")
log(f"    Median agg: std={median_agg.std():.2f}, range=[{median_agg.min():.1f}, {median_agg.max():.1f}]")

# ═════════════════════════════════════════════════════════════════════════════
# STEP 3: Temporal train/test split
# ═════════════════════════════════════════════════════════════════════════════
train_end = pd.Timestamp("2022-07-18")
test_start = pd.Timestamp("2022-07-19")

train = cluster_ts[cluster_ts["datetime_hour"] <= train_end].copy()
test = cluster_ts[cluster_ts["datetime_hour"] >= test_start].copy()

log(f"\n[3] Temporal split:")
log(f"    Train: {len(train)} rows ({train['datetime_hour'].min()} to {train['datetime_hour'].max()})")
log(f"    Test:  {len(test)} rows ({test['datetime_hour'].min()} to {test['datetime_hour'].max()})")

# ═════════════════════════════════════════════════════════════════════════════
# STEP 4: Winsorization (99th percentile, caps from training data ONLY)
# ═════════════════════════════════════════════════════════════════════════════
log(f"\n[4] Winsorization (99th percentile capping)")
PERCENTILE = 0.99

latency_cap = train["target_latency"].quantile(PERCENTILE)
throughput_cap = train["target_throughput"].quantile(PERCENTILE)
log(f"    Latency cap (99th pct of train):    {latency_cap:.2f} ms")
log(f"    Throughput cap (99th pct of train):  {throughput_cap:.2f} Mbps")

latency_cols = ["svr1", "target_latency", "latency_lag_1h", "latency_rolling_3h", "latency_rolling_6h"]
throughput_cols = ["upload_bitrate_mbps", "download_bitrate_mbps", "target_throughput",
                   "throughput_lag_1h", "throughput_rolling_3h", "throughput_rolling_6h"]

winsorize_stats = []

for col in latency_cols:
    if col in train.columns:
        n_train = int((train[col] > latency_cap).sum())
        n_test = int((test[col] > latency_cap).sum())
        max_before_train = float(train[col].max())
        max_before_test = float(test[col].max())
        train[col] = train[col].clip(upper=latency_cap)
        test[col] = test[col].clip(upper=latency_cap)
        winsorize_stats.append({
            "column": col, "cap_type": "latency", "cap_value": round(latency_cap, 2),
            "train_clipped": n_train, "test_clipped": n_test,
            "train_max_before": round(max_before_train, 2), "train_max_after": round(float(train[col].max()), 2),
            "test_max_before": round(max_before_test, 2), "test_max_after": round(float(test[col].max()), 2),
        })
        if n_train > 0 or n_test > 0:
            log(f"    {col}: train={n_train} clipped, test={n_test} clipped")

for col in throughput_cols:
    if col in train.columns:
        n_train = int((train[col] > throughput_cap).sum())
        n_test = int((test[col] > throughput_cap).sum())
        max_before_train = float(train[col].max())
        max_before_test = float(test[col].max())
        train[col] = train[col].clip(upper=throughput_cap)
        test[col] = test[col].clip(upper=throughput_cap)
        winsorize_stats.append({
            "column": col, "cap_type": "throughput", "cap_value": round(throughput_cap, 2),
            "train_clipped": n_train, "test_clipped": n_test,
            "train_max_before": round(max_before_train, 2), "train_max_after": round(float(train[col].max()), 2),
            "test_max_before": round(max_before_test, 2), "test_max_after": round(float(test[col].max()), 2),
        })
        if n_train > 0 or n_test > 0:
            log(f"    {col}: train={n_train} clipped, test={n_test} clipped")

pd.DataFrame(winsorize_stats).to_csv(os.path.join(V2_OUT, "winsorization_summary.csv"), index=False)

# Also cap cluster_ts for LSTM windowing
for col in latency_cols:
    if col in cluster_ts.columns:
        cluster_ts[col] = cluster_ts[col].clip(upper=latency_cap)
for col in throughput_cols:
    if col in cluster_ts.columns:
        cluster_ts[col] = cluster_ts[col].clip(upper=throughput_cap)

train.to_csv(os.path.join(V2_OUT, "train_set.csv"), index=False)
test.to_csv(os.path.join(V2_OUT, "test_set.csv"), index=False)
cluster_ts.to_csv(os.path.join(V2_OUT, "cluster_timeseries_winsorized.csv"), index=False)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 5: ARIMA Forecasting
# ═════════════════════════════════════════════════════════════════════════════
log(f"\n[5] ARIMA Forecasting")
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
            }

            arima_all_metrics.append({
                "target": target, "cluster": int(cluster_id), "model": "ARIMA",
                "rmse": round(rmse, 4), "mae": round(mae, 4), "mape": round(mape, 2),
                "order": str(model.order),
            })

            log(f"  Cluster {cluster_id}: order={model.order}, RMSE={rmse:.2f}, MAE={mae:.2f}, MAPE={mape:.1f}%")

            # Save predictions
            pred_df = pd.DataFrame({"actual": c_test, "predicted": preds})
            pred_df.to_csv(os.path.join(V2_OUT, f"arima_{target}_cluster{cluster_id}_predictions.csv"), index=False)
        except Exception as e:
            log(f"  Cluster {cluster_id}: ARIMA failed -- {e}")

# Save ARIMA results pkl
with open(os.path.join(V2_OUT, "arima_results.pkl"), "wb") as f:
    arima_save = {k: {kk: vv for kk, vv in v.items()} for k, v in arima_results.items()}
    pickle.dump(arima_save, f)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 6: LSTM Forecasting (MAE LOSS — PRIMARY CHANGE)
# ═════════════════════════════════════════════════════════════════════════════
log(f"\n[6] LSTM Forecasting (loss=MAE)")

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

        # Same architecture, but loss='mae' instead of 'mse'
        model = Sequential([
            LSTM(32, input_shape=(WINDOW_SIZE, len(all_cols)), return_sequences=True),
            Dropout(0.2),
            LSTM(16),
            Dropout(0.2),
            Dense(1)
        ])
        model.compile(optimizer="adam", loss="mae")  # <-- CHANGED from mse to mae

        early_stop = EarlyStopping(patience=10, restore_best_weights=True, verbose=0)
        history = model.fit(X_train, y_train, epochs=100, batch_size=16,
                            validation_split=0.2, callbacks=[early_stop], verbose=0)

        epochs_trained = len(history.history["loss"])
        final_train_loss = history.history["loss"][-1]
        final_val_loss = history.history["val_loss"][-1]

        preds_scaled = model.predict(X_test, verbose=0).flatten()

        # Inverse transform
        dummy = np.zeros((len(preds_scaled), len(all_cols)))
        dummy[:, target_idx] = preds_scaled
        preds_inv = scaler_lstm.inverse_transform(dummy)[:, target_idx]

        dummy_actual = np.zeros((len(y_test), len(all_cols)))
        dummy_actual[:, target_idx] = y_test
        actual_inv = scaler_lstm.inverse_transform(dummy_actual)[:, target_idx]

        rmse = float(np.sqrt(mean_squared_error(actual_inv, preds_inv)))
        mae_val = float(mean_absolute_error(actual_inv, preds_inv))
        nonzero = actual_inv != 0
        mape = float(np.mean(np.abs((actual_inv[nonzero] - preds_inv[nonzero]) / actual_inv[nonzero])) * 100) if nonzero.any() else float("nan")

        lstm_results[(target, cluster_id)] = {
            "preds": preds_inv, "actual": actual_inv,
            "rmse": rmse, "mae": mae_val, "mape": mape,
        }

        lstm_all_metrics.append({
            "target": target, "cluster": int(cluster_id), "model": "LSTM",
            "rmse": round(rmse, 4), "mae": round(mae_val, 4), "mape": round(mape, 2),
            "window_size": WINDOW_SIZE, "epochs_trained": epochs_trained,
            "final_train_loss": round(float(final_train_loss), 6),
            "final_val_loss": round(float(final_val_loss), 6),
            "train_sequences": len(X_train), "test_sequences": len(X_test),
            "features": str(features), "loss_function": "mae",
        })

        log(f"       epochs={epochs_trained}, train_loss={final_train_loss:.6f}, val_loss={final_val_loss:.6f}")
        log(f"       RMSE={rmse:.2f}, MAE={mae_val:.2f}, MAPE={mape:.1f}%")

        # Save predictions
        pred_df = pd.DataFrame({"actual": actual_inv, "predicted": preds_inv})
        pred_df.to_csv(os.path.join(V2_OUT, f"lstm_{target}_cluster{cluster_id}_predictions.csv"), index=False)

        # Save training history
        hist_df = pd.DataFrame({
            "epoch": range(1, epochs_trained + 1),
            "train_loss": history.history["loss"],
            "val_loss": history.history["val_loss"]
        })
        hist_df.to_csv(os.path.join(V2_OUT, f"lstm_{target}_cluster{cluster_id}_training_history.csv"), index=False)

        # Save model as .h5
        model.save(os.path.join(V2_OUT, f"lstm_{target}_cluster{cluster_id}.h5"))

# Save LSTM results pkl
with open(os.path.join(V2_OUT, "lstm_results.pkl"), "wb") as f:
    pickle.dump(lstm_results, f)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 7: Save combined metrics
# ═════════════════════════════════════════════════════════════════════════════
all_metrics = arima_all_metrics + lstm_all_metrics
metrics_df = pd.DataFrame(all_metrics)
metrics_df.to_csv(os.path.join(V2_OUT, "all_forecasting_metrics.csv"), index=False)

# Also save KMeans model + scaler (copied from existing outputs for completeness)
import shutil
for f_name in ["kmeans_model.pkl", "scaler.pkl", "clustering_meta.pkl"]:
    src = os.path.join(BASE, "outputs", f_name)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(V2_OUT, f_name))

# ═════════════════════════════════════════════════════════════════════════════
# STEP 8: Forecast plots
# ═════════════════════════════════════════════════════════════════════════════
log(f"\n[7] Generating forecast plots")

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
            ax.plot(range(len(r["preds"])), r["preds"], "g--^", label=f"LSTM-MAE (RMSE={r['rmse']:.2f})", markersize=3)

        ax.set_title(f"V2 (Median+MAE) | Cluster {cluster_id} - {target}")
        ax.set_xlabel("Time Step")
        ax.set_ylabel(target)
        ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(V2_OUT, f"forecast_{target}.png"), dpi=150, bbox_inches="tight")
    plt.close()

# ═════════════════════════════════════════════════════════════════════════════
# STEP 9: Side-by-side comparison
# ═════════════════════════════════════════════════════════════════════════════
log(f"\n{'='*70}")
log(f"SIDE-BY-SIDE COMPARISON: V1 (mean+MSE) vs V2 (median+MAE)")
log(f"{'='*70}")

old_metrics = [
    {"target": "Latency", "cluster": 0, "model": "ARIMA", "rmse": 39.53, "mae": 27.23, "mape": 29.0},
    {"target": "Latency", "cluster": 0, "model": "LSTM", "rmse": 28.48, "mae": 23.90, "mape": 27.6},
    {"target": "Latency", "cluster": 1, "model": "ARIMA", "rmse": 71.57, "mae": 61.28, "mape": 39.0},
    {"target": "Latency", "cluster": 1, "model": "LSTM", "rmse": 46.08, "mae": 36.41, "mape": 20.9},
    {"target": "Throughput", "cluster": 0, "model": "ARIMA", "rmse": 16.12, "mae": 9.15, "mape": 18.8},
    {"target": "Throughput", "cluster": 0, "model": "LSTM", "rmse": 14.93, "mae": 8.10, "mape": 17.2},
    {"target": "Throughput", "cluster": 1, "model": "ARIMA", "rmse": 5.93, "mae": 4.61, "mape": 17.9},
    {"target": "Throughput", "cluster": 1, "model": "LSTM", "rmse": 5.91, "mae": 4.35, "mape": 16.3},
]

# Map old target names to new
target_name_map = {"Latency": "target_latency", "Throughput": "target_throughput"}

header = f"{'Target':<20} {'Cl':<4} {'Model':<7} | {'V1 RMSE':<9} {'V2 RMSE':<9} {'Chg':<8} | {'V1 MAE':<8} {'V2 MAE':<8} {'Chg':<8} | {'V1 MAPE':<8} {'V2 MAPE':<8} {'Chg':<8}"
log(f"\n{header}")
log("-" * len(header))

comparison_rows = []

for old in old_metrics:
    target_new = target_name_map[old["target"]]
    cluster_id = old["cluster"]
    model_name = old["model"]

    # Find matching new metric
    new_match = None
    for m in all_metrics:
        if m["target"] == target_new and m["cluster"] == cluster_id and m["model"] == model_name:
            new_match = m
            break

    if new_match:
        rmse_chg = ((new_match["rmse"] - old["rmse"]) / old["rmse"]) * 100
        mae_chg = ((new_match["mae"] - old["mae"]) / old["mae"]) * 100
        mape_chg = ((new_match["mape"] - old["mape"]) / old["mape"]) * 100

        rmse_arrow = "v" if rmse_chg < 0 else "^"
        mae_arrow = "v" if mae_chg < 0 else "^"
        mape_arrow = "v" if mape_chg < 0 else "^"

        log(f"{old['target']:<20} {cluster_id:<4} {model_name:<7} | "
            f"{old['rmse']:<9.2f} {new_match['rmse']:<9.2f} {rmse_chg:+.1f}%{rmse_arrow} | "
            f"{old['mae']:<8.2f} {new_match['mae']:<8.2f} {mae_chg:+.1f}%{mae_arrow} | "
            f"{old['mape']:<8.1f} {new_match['mape']:<8.1f} {mape_chg:+.1f}%{mape_arrow}")

        comparison_rows.append({
            "target": old["target"], "cluster": cluster_id, "model": model_name,
            "v1_rmse": old["rmse"], "v2_rmse": new_match["rmse"], "rmse_change_pct": round(rmse_chg, 1),
            "v1_mae": old["mae"], "v2_mae": new_match["mae"], "mae_change_pct": round(mae_chg, 1),
            "v1_mape": old["mape"], "v2_mape": new_match["mape"], "mape_change_pct": round(mape_chg, 1),
        })
    else:
        log(f"{old['target']:<20} {cluster_id:<4} {model_name:<7} | NO V2 MATCH")

pd.DataFrame(comparison_rows).to_csv(os.path.join(V2_OUT, "v1_vs_v2_comparison.csv"), index=False)

log(f"\nLegend: v = improved (lower), ^ = worse (higher)")
log(f"\nAll V2 outputs saved to {V2_OUT}/")
log(f"Done!")

log_file.close()
