"""
SageMaker Training Job — XGBoost + LSTM + 1D CNN Forecasting Benchmark.

Replicates the full pipeline from Notebook 3 (3_model_forecasting.ipynb):
  1. Load cleaned_5g_data.csv, reconstruct targets, aggregate hourly per zone
  2. Grid-fill + proper temporal lag features (lag1–lag3, rolling mean, upload lags)
  3. Train XGBoost (25 features), LSTM (128→64), 1D CNN (128→64)
  4. Benchmark (R², MAE, RMSE) — select winner by best avg R²
  5. Autoregressive 12-hour dashboard forecast → metrics/forecast_data.csv
  6. Save model artefacts + pipeline_config.pkl

Frontend contract: metrics/forecast_data.csv with 12 rows:
  timestamp, predicted_throughput, predicted_latency
"""
import argparse
import os
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler
from xgboost import XGBRegressor

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import (
    LSTM, Conv1D, Dense, Dropout, Flatten, MaxPooling1D,
)
from tensorflow.keras.models import Sequential

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Config ──────────────────────────────────────────────────────
TARGETS = ["download_mbps", "avg_latency"]
SEQ_LEN = 6
SPLIT_HOURS = 48
TOP_N_ZONES = 5
LAG_STEPS = 3
FORECAST_STEPS = 12
RANDOM_STATE = 42

AUX_COLS = [
    "svr1", "jitter", "retransmission_rate", "congestion_indicator",
    "upload_mbps_lag1", "download_mbps_roll5_std", "cwnd_x_speed",
    "CWnd", "cwnd_to_latency",
]

TREE_FEATURES = [
    "hour_sin", "hour_cos", "is_weekend",
    "zone_mean_dl", "zone_mean_lat",
    "download_mbps_lag1", "download_mbps_lag2", "download_mbps_lag3",
    "avg_latency_lag1", "avg_latency_lag2", "avg_latency_lag3",
    "upload_lag1", "upload_lag2", "upload_lag3",
    "download_mbps_rmean3", "avg_latency_rmean3",
    "svr1", "jitter", "retransmission_rate", "congestion_indicator",
    "upload_mbps_lag1", "download_mbps_roll5_std", "cwnd_x_speed",
    "CWnd", "cwnd_to_latency",
]


def create_sequences(
    df_scaled: pd.DataFrame,
    window_cols: list[str],
    target_idx: list[int],
    seq_len: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list, np.ndarray]:
    """Build per-zone sliding windows from the scaled filled grid."""
    X, y, ts, zones, real_flags = [], [], [], [], []
    for zone_id, zone_df in df_scaled.groupby("square_id"):
        zone_df = zone_df.sort_values("timestamp")
        vals = zone_df[window_cols].values
        timestamps = zone_df["timestamp"].values
        is_real = zone_df["is_real"].values
        for i in range(len(vals) - seq_len):
            X.append(vals[i: i + seq_len])
            y.append(vals[i + seq_len, target_idx])
            ts.append(timestamps[i + seq_len])
            zones.append(zone_id)
            real_flags.append(is_real[i + seq_len])
    return np.array(X), np.array(y), np.array(ts), zones, np.array(real_flags)


def main() -> None:
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

    # ================================================================
    # Step 1a — Load & reconstruct targets
    # ================================================================
    df_raw = pd.read_csv(input_dir / "cleaned_5g_data.csv", low_memory=False)
    df_raw["Timestamp"] = pd.to_datetime(df_raw["Timestamp"])
    df_raw["download_mbps"] = np.expm1(df_raw["log_download"])
    df_raw["avg_latency"] = df_raw["avg_latency_lag1"]

    for col in TARGETS:
        df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")

    df_raw["date"] = df_raw["Timestamp"].dt.date
    df_raw["hour"] = df_raw["Timestamp"].dt.hour
    print(f"Loaded: {len(df_raw):,} rows")

    # ================================================================
    # Step 1b — Aggregate → hourly zone means + grid-fill
    # ================================================================
    AGG_COLS = TARGETS + AUX_COLS
    for c in AUX_COLS:
        df_raw[c] = pd.to_numeric(df_raw[c], errors="coerce")

    agg_raw = (
        df_raw
        .groupby(["square_id", "date", "hour"])[AGG_COLS]
        .mean()
        .reset_index()
    )
    agg_raw["date"] = pd.to_datetime(agg_raw["date"])
    agg_raw["timestamp"] = agg_raw["date"] + pd.to_timedelta(agg_raw["hour"], unit="h")
    agg_raw.dropna(subset=TARGETS, inplace=True)
    agg_raw.sort_values(["square_id", "timestamp"], inplace=True)
    agg_raw.reset_index(drop=True, inplace=True)

    for c in AUX_COLS:
        agg_raw[c].fillna(agg_raw[c].mean(), inplace=True)

    print(f"Aggregated: {len(agg_raw):,} hourly zone-blocks")

    # Grid-fill per zone
    filled_parts: list[pd.DataFrame] = []
    for zone, grp in agg_raw.groupby("square_id"):
        rng = pd.date_range(start=grp["timestamp"].min(),
                            end=grp["timestamp"].max(), freq="h")
        full = pd.DataFrame({"timestamp": rng, "square_id": zone})
        full = full.merge(grp.drop(columns=["square_id"]), on="timestamp", how="left")
        full["is_real"] = full[TARGETS[0]].notna()
        full[AGG_COLS] = full[AGG_COLS].ffill()
        full.dropna(subset=TARGETS, inplace=True)
        filled_parts.append(full)

    agg_filled = pd.concat(filled_parts, ignore_index=True)
    agg_filled.sort_values(["square_id", "timestamp"], inplace=True)
    agg_filled.reset_index(drop=True, inplace=True)
    print(f"Grid-filled: {len(agg_filled):,} zone-hours")

    # ================================================================
    # Step 1c — Lag features on the filled grid
    # ================================================================
    for lag in range(1, LAG_STEPS + 1):
        for tgt in TARGETS:
            agg_filled[f"{tgt}_lag{lag}"] = agg_filled.groupby("square_id")[tgt].shift(lag)
        agg_filled[f"upload_lag{lag}"] = (
            agg_filled.groupby("square_id")["upload_mbps_lag1"].shift(lag)
        )

    for tgt in TARGETS:
        agg_filled[f"{tgt}_rmean3"] = (
            agg_filled.groupby("square_id")[tgt]
            .transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
        )

    lag_cols = [f"{t}_lag{l}" for t in TARGETS for l in range(1, LAG_STEPS + 1)]
    upload_lag_cols = [f"upload_lag{l}" for l in range(1, LAG_STEPS + 1)]
    all_lag_cols = lag_cols + upload_lag_cols
    agg_filled.dropna(subset=all_lag_cols, inplace=True)
    agg_filled.reset_index(drop=True, inplace=True)

    # ================================================================
    # Step 1d — Keep only REAL rows for XGBoost
    # ================================================================
    agg_df = agg_filled[agg_filled["is_real"]].copy()
    agg_df.reset_index(drop=True, inplace=True)
    agg_df["date"] = pd.to_datetime(agg_df["timestamp"].dt.date)
    agg_df["hour"] = agg_df["timestamp"].dt.hour
    print(f"Real rows after lag drop: {len(agg_df):,}")

    # ================================================================
    # Step 1e — Temporal features + zone encoding
    # ================================================================
    for frame in [agg_df, agg_filled]:
        frame["hour_sin"] = np.sin(2 * np.pi * frame["timestamp"].dt.hour / 24)
        frame["hour_cos"] = np.cos(2 * np.pi * frame["timestamp"].dt.hour / 24)
        frame["is_weekend"] = (frame["timestamp"].dt.dayofweek >= 5).astype(int)

    cutoff = agg_df["timestamp"].max() - pd.Timedelta(hours=SPLIT_HOURS)
    train_mask = agg_df["timestamp"] <= cutoff
    test_mask = agg_df["timestamp"] > cutoff

    zone_enc_dl = agg_df.loc[train_mask].groupby("square_id")["download_mbps"].mean()
    zone_enc_lat = agg_df.loc[train_mask].groupby("square_id")["avg_latency"].mean()
    global_mean_dl = float(agg_df.loc[train_mask, "download_mbps"].mean())
    global_mean_lat = float(agg_df.loc[train_mask, "avg_latency"].mean())

    for frame in [agg_df, agg_filled]:
        frame["zone_mean_dl"] = frame["square_id"].map(zone_enc_dl).fillna(global_mean_dl)
        frame["zone_mean_lat"] = frame["square_id"].map(zone_enc_lat).fillna(global_mean_lat)

    zone_aux_means: dict[str, pd.Series] = {}
    for c in AUX_COLS:
        zone_aux_means[c] = agg_df.loc[train_mask].groupby("square_id")[c].mean()

    print(f"Train: {train_mask.sum():,}  |  Test: {test_mask.sum():,}")

    # ================================================================
    # Step 2 — Scaling & sequence windowing
    # ================================================================
    WINDOW_COLS = TREE_FEATURES + TARGETS
    TARGET_IDX = [WINDOW_COLS.index(t) for t in TARGETS]

    train_df = agg_df[train_mask].copy()
    test_df = agg_df[test_mask].copy()

    X_train_tree = train_df[TREE_FEATURES].values
    X_test_tree = test_df[TREE_FEATURES].values
    y_train_tree = train_df[TARGETS].values
    y_test_tree = test_df[TARGETS].values

    scaler = MinMaxScaler()
    scaler.fit(train_df[WINDOW_COLS])

    agg_scaled = agg_df.copy()
    agg_scaled[WINDOW_COLS] = scaler.transform(agg_df[WINDOW_COLS])

    agg_filled_scaled = agg_filled.copy()
    agg_filled_scaled[WINDOW_COLS] = scaler.transform(agg_filled[WINDOW_COLS])

    target_min = scaler.data_min_[TARGET_IDX]
    target_range = scaler.data_range_[TARGET_IDX]

    # Build DL sliding windows
    X_seq, y_seq, ts_seq, zone_seq, real_seq = create_sequences(
        agg_filled_scaled, WINDOW_COLS, TARGET_IDX, SEQ_LEN,
    )

    cutoff_np = np.datetime64(cutoff)
    seq_train_mask = (ts_seq <= cutoff_np) & real_seq
    seq_test_mask = (ts_seq > cutoff_np) & real_seq

    X_train_seq = X_seq[seq_train_mask]
    y_train_seq = y_seq[seq_train_mask]
    X_test_seq = X_seq[seq_test_mask]
    y_test_seq = y_seq[seq_test_mask]

    print(f"DL windows → Train: {X_train_seq.shape[0]:,}  Test: {X_test_seq.shape[0]:,}")

    # ================================================================
    # Step 3a — XGBoost
    # ================================================================
    xgb_models: dict[str, XGBRegressor] = {}
    all_results: list[dict] = []

    for i, tgt in enumerate(TARGETS):
        model = XGBRegressor(
            n_estimators=1000, max_depth=8, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
            reg_alpha=0.1, reg_lambda=1.0,
            tree_method="hist", random_state=RANDOM_STATE, verbosity=0, n_jobs=-1,
        )
        model.fit(X_train_tree, y_train_tree[:, i])
        y_pred = model.predict(X_test_tree)
        y_true = y_test_tree[:, i]

        r2 = r2_score(y_true, y_pred)
        mae = mean_absolute_error(y_true, y_pred)
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))

        xgb_models[tgt] = model
        all_results.append({
            "Model": "XGBoost", "Target": tgt,
            "R2": round(r2, 4), "MAE": round(mae, 3), "RMSE": round(rmse, 3),
        })
        print(f"XGBoost → {tgt:20s}  R²={r2:.4f}  MAE={mae:.3f}  RMSE={rmse:.3f}")

    # ================================================================
    # Step 3b — LSTM
    # ================================================================
    tf.random.set_seed(RANDOM_STATE)
    n_features = X_train_seq.shape[2]
    n_targets = len(TARGETS)

    model_lstm = Sequential([
        LSTM(128, return_sequences=True, input_shape=(SEQ_LEN, n_features)),
        Dropout(0.2),
        LSTM(64),
        Dropout(0.2),
        Dense(32, activation="relu"),
        Dense(n_targets),
    ])
    model_lstm.compile(optimizer="adam", loss="mse")

    early_stop = EarlyStopping(
        monitor="val_loss", patience=5, restore_best_weights=True, verbose=1,
    )
    model_lstm.fit(
        X_train_seq, y_train_seq,
        epochs=80, batch_size=32, validation_split=0.15,
        callbacks=[early_stop], verbose=1,
    )

    y_pred_lstm_scaled = model_lstm.predict(X_test_seq, verbose=0)
    y_pred_lstm = y_pred_lstm_scaled * target_range + target_min
    y_test_real = y_test_seq * target_range + target_min

    for i, tgt in enumerate(TARGETS):
        r2 = r2_score(y_test_real[:, i], y_pred_lstm[:, i])
        mae = mean_absolute_error(y_test_real[:, i], y_pred_lstm[:, i])
        rmse = float(np.sqrt(mean_squared_error(y_test_real[:, i], y_pred_lstm[:, i])))
        all_results.append({
            "Model": "LSTM", "Target": tgt,
            "R2": round(r2, 4), "MAE": round(mae, 3), "RMSE": round(rmse, 3),
        })
        print(f"LSTM → {tgt:20s}  R²={r2:.4f}  MAE={mae:.3f}  RMSE={rmse:.3f}")

    # ================================================================
    # Step 3c — 1D CNN
    # ================================================================
    tf.random.set_seed(RANDOM_STATE)

    model_cnn = Sequential([
        Conv1D(128, kernel_size=3, activation="relu", input_shape=(SEQ_LEN, n_features)),
        MaxPooling1D(pool_size=2),
        Conv1D(64, kernel_size=2, activation="relu"),
        Flatten(),
        Dropout(0.2),
        Dense(64, activation="relu"),
        Dense(32, activation="relu"),
        Dense(n_targets),
    ])
    model_cnn.compile(optimizer="adam", loss="mse")

    early_stop_cnn = EarlyStopping(
        monitor="val_loss", patience=5, restore_best_weights=True, verbose=1,
    )
    model_cnn.fit(
        X_train_seq, y_train_seq,
        epochs=80, batch_size=32, validation_split=0.15,
        callbacks=[early_stop_cnn], verbose=1,
    )

    y_pred_cnn_scaled = model_cnn.predict(X_test_seq, verbose=0)
    y_pred_cnn = y_pred_cnn_scaled * target_range + target_min

    for i, tgt in enumerate(TARGETS):
        r2 = r2_score(y_test_real[:, i], y_pred_cnn[:, i])
        mae = mean_absolute_error(y_test_real[:, i], y_pred_cnn[:, i])
        rmse = float(np.sqrt(mean_squared_error(y_test_real[:, i], y_pred_cnn[:, i])))
        all_results.append({
            "Model": "1D_CNN", "Target": tgt,
            "R2": round(r2, 4), "MAE": round(mae, 3), "RMSE": round(rmse, 3),
        })
        print(f"1D CNN → {tgt:20s}  R²={r2:.4f}  MAE={mae:.3f}  RMSE={rmse:.3f}")

    # ================================================================
    # Step 4 — Winner selection
    # ================================================================
    comparison = pd.DataFrame(all_results)
    avg_r2 = comparison.groupby("Model")["R2"].mean().sort_values(ascending=False)
    print(f"\nAverage R² by model:\n{avg_r2.to_string()}")

    WINNER_NAME = str(avg_r2.idxmax())
    IS_DL_WINNER = WINNER_NAME in {"LSTM", "1D_CNN"}
    DL_MODELS = {"LSTM": model_lstm, "1D_CNN": model_cnn}

    print(f"\n🏆 Winner: {WINNER_NAME}  (avg R² = {avg_r2.max():.4f})")

    if IS_DL_WINNER:
        winner_model = DL_MODELS[WINNER_NAME]
    else:
        winner_model = xgb_models

    # ================================================================
    # Step 5 — 12-hour autoregressive dashboard forecast
    # ================================================================
    top_zones = agg_df["square_id"].value_counts().head(TOP_N_ZONES).index.tolist()
    last_ts = agg_df["timestamp"].max()

    col_idx = {c: i for i, c in enumerate(WINDOW_COLS)}

    def build_forecast_row(
        ts: pd.Timestamp,
        zone: str,
        recent_dl: list[float],
        recent_lat: list[float],
        recent_ul: list[float],
        zone_aux: dict[str, float],
    ) -> np.ndarray:
        """Build a single WINDOW_COLS row (unscaled) for the next forecast step."""
        h = ts.hour
        dow = ts.dayofweek
        row = np.zeros(len(WINDOW_COLS))

        row[col_idx["hour_sin"]] = np.sin(2 * np.pi * h / 24)
        row[col_idx["hour_cos"]] = np.cos(2 * np.pi * h / 24)
        row[col_idx["is_weekend"]] = int(dow >= 5)

        row[col_idx["zone_mean_dl"]] = zone_enc_dl.get(zone, global_mean_dl)
        row[col_idx["zone_mean_lat"]] = zone_enc_lat.get(zone, global_mean_lat)

        for lag in range(1, LAG_STEPS + 1):
            row[col_idx[f"download_mbps_lag{lag}"]] = recent_dl[-lag]
            row[col_idx[f"avg_latency_lag{lag}"]] = recent_lat[-lag]
            row[col_idx[f"upload_lag{lag}"]] = recent_ul[-lag]

        row[col_idx["download_mbps_rmean3"]] = np.mean(recent_dl[-3:])
        row[col_idx["avg_latency_rmean3"]] = np.mean(recent_lat[-3:])

        for c in AUX_COLS:
            row[col_idx[c]] = zone_aux[c]

        row[col_idx["download_mbps"]] = recent_dl[-1]
        row[col_idx["avg_latency"]] = recent_lat[-1]

        return row

    all_zone_preds: list[pd.DataFrame] = []

    for zone in top_zones:
        zone_data = agg_df[agg_df["square_id"] == zone].sort_values("timestamp")
        zone_data_scaled = agg_scaled[agg_scaled["square_id"] == zone].sort_values("timestamp")

        if len(zone_data) < max(SEQ_LEN, LAG_STEPS):
            continue

        hist_dl = zone_data["download_mbps"].values[-max(SEQ_LEN, LAG_STEPS):].tolist()
        hist_lat = zone_data["avg_latency"].values[-max(SEQ_LEN, LAG_STEPS):].tolist()

        if "upload_mbps_lag1" in zone_data.columns:
            hist_ul = zone_data["upload_mbps_lag1"].values[-max(SEQ_LEN, LAG_STEPS):].tolist()
        else:
            ul_mean = float(zone_aux_means["upload_mbps_lag1"].get(
                zone, agg_df["upload_mbps_lag1"].mean()))
            hist_ul = [ul_mean] * max(SEQ_LEN, LAG_STEPS)

        zone_aux = {c: float(zone_aux_means[c].get(zone, agg_df[c].mean())) for c in AUX_COLS}

        if IS_DL_WINNER:
            window = zone_data_scaled[WINDOW_COLS].values[-SEQ_LEN:]
            preds_real = []
            ts = last_ts

            for _ in range(FORECAST_STEPS):
                pred_scaled = winner_model.predict(window[np.newaxis], verbose=0)[0]
                pred_real = pred_scaled * target_range + target_min
                pred_real = np.clip(pred_real, 0, None)
                preds_real.append(pred_real)

                hist_dl.append(float(pred_real[0]))
                hist_lat.append(float(pred_real[1]))
                hist_ul.append(zone_aux["upload_mbps_lag1"])
                ts = ts + pd.Timedelta(hours=1)

                next_row_unscaled = build_forecast_row(ts, zone, hist_dl, hist_lat, hist_ul, zone_aux)
                next_row_scaled = (next_row_unscaled - scaler.data_min_) / scaler.data_range_
                next_row_scaled = np.clip(next_row_scaled, 0, 1)
                window = np.vstack([window[1:], next_row_scaled[np.newaxis]])

            zone_forecast = pd.DataFrame(preds_real, columns=TARGETS)
        else:
            preds = []
            for step in range(FORECAST_STEPS):
                ts = last_ts + pd.Timedelta(hours=step + 1)
                feat_row = build_forecast_row(ts, zone, hist_dl, hist_lat, hist_ul, zone_aux)
                X_row = np.array([[feat_row[col_idx[f]] for f in TREE_FEATURES]])
                pred_pair = np.array([
                    float(np.clip(xgb_models[tgt].predict(X_row)[0], 0, None))
                    for tgt in TARGETS
                ])
                preds.append(pred_pair)
                hist_dl.append(pred_pair[0])
                hist_lat.append(pred_pair[1])
                hist_ul.append(zone_aux["upload_mbps_lag1"])

            zone_forecast = pd.DataFrame(preds, columns=TARGETS)

        zone_forecast["timestamp"] = pd.date_range(
            start=last_ts + pd.Timedelta(hours=1), periods=FORECAST_STEPS, freq="h"
        )
        all_zone_preds.append(zone_forecast)

    # Aggregate across zones → exactly 12 rows
    future_all = pd.concat(all_zone_preds, ignore_index=True)
    forecast_export = (
        future_all
        .groupby("timestamp")[TARGETS]
        .mean()
        .reset_index()
        .rename(columns={
            "download_mbps": "predicted_throughput",
            "avg_latency": "predicted_latency",
        })
    )

    forecast_path = output_dir / "forecast_data.csv"
    forecast_export.to_csv(forecast_path, index=False)
    print(f"✅ Exported {len(forecast_export)} rows → {forecast_path}")

    # ================================================================
    # Step 6 — Save model artefacts
    # ================================================================
    if IS_DL_WINNER:
        winner_model.save(model_dir / "forecasting_model.h5")
        print(f"💾 Saved Keras model → forecasting_model.h5")
    else:
        for tgt in TARGETS:
            p = model_dir / f"xgboost_{tgt}.pkl"
            joblib.dump(xgb_models[tgt], p)
            print(f"💾 Saved: {p.name}")

    # Pipeline config (scaler + encoding + metadata)
    enc_artifact = {
        "scaler": scaler,
        "zone_enc_dl": zone_enc_dl.to_dict(),
        "zone_enc_lat": zone_enc_lat.to_dict(),
        "zone_aux_means": {c: zone_aux_means[c].to_dict() for c in AUX_COLS},
        "global_mean_dl": global_mean_dl,
        "global_mean_lat": global_mean_lat,
        "target_min": target_min.tolist(),
        "target_range": target_range.tolist(),
        "window_cols": WINDOW_COLS,
        "tree_features": TREE_FEATURES,
        "targets": TARGETS,
        "aux_cols": AUX_COLS,
        "lag_steps": LAG_STEPS,
        "seq_len": SEQ_LEN,
        "top_zones": top_zones,
        "winner": WINNER_NAME,
        "is_dl": IS_DL_WINNER,
    }
    joblib.dump(enc_artifact, model_dir / "pipeline_config.pkl")
    print(f"💾 Saved: pipeline_config.pkl")

    # Save comparison results
    comparison.to_csv(output_dir / "model_benchmark.csv", index=False)
    print(f"✅ All artefacts saved. Winner: {WINNER_NAME}")


if __name__ == "__main__":
    main()