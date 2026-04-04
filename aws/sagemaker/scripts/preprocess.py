"""
SageMaker Processing Job — Data Preprocessing & Feature Engineering.

Replicates the full pipeline from Notebook 1 (1_data_preprocessing.ipynb):
  1. Load & concatenate raw CSVs
  2. Strict cleaning (Timestamp, GPS sentinels, bounding box, timeouts, negatives)
  3. Regular 1-second resampling per (truck, square_id) session
  4. Dtype optimisation
  5. Feature engineering (temporal, network/telecom, stationarity, outlier capping,
     lag/rolling, feature selection, geospatial, train/val split)
  6. Export cleaned_5g_data.csv
"""
import argparse
import glob
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ── Melbourne / Brimbank bounding box ──
LAT_MIN, LAT_MAX = -37.85, -37.70
LON_MIN, LON_MAX = 144.75, 144.90
MAX_GAP_S = 60  # session boundary threshold (seconds)
CORR_THRESHOLD = 0.95
CBD_LAT, CBD_LON = -37.8183, 144.9671  # Flinders St Station


def _optimise_dtypes(frame: pd.DataFrame) -> pd.DataFrame:
    """Down-cast numeric columns to smallest viable dtype."""
    for col in frame.select_dtypes(include=["float64"]).columns:
        frame[col] = pd.to_numeric(frame[col], downcast="float")
    for col in frame.select_dtypes(include=["int64"]).columns:
        frame[col] = pd.to_numeric(frame[col], downcast="integer")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=str, default="/opt/ml/processing/input")
    parser.add_argument("--output-dir", type=str, default="/opt/ml/processing/output")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ================================================================
    # Step 1 — Load & concatenate all raw CSVs
    # ================================================================
    csv_files = sorted(glob.glob(str(input_dir / "*.csv")))
    csv_files = [f for f in csv_files
                 if Path(f).stem not in ("cleaned_5g_data", "map_data")]
    print(f"Found {len(csv_files)} raw CSV files")

    frames = []
    for fp in csv_files:
        try:
            tmp = pd.read_csv(fp, low_memory=False)
            tmp["source_file"] = Path(fp).stem
            frames.append(tmp)
        except Exception as exc:
            print(f"  ⚠ skipped {fp}: {exc}")

    df = pd.concat(frames, ignore_index=True)
    rows_before = len(df)
    print(f"Combined shape: {df.shape}")

    # ================================================================
    # Step 2 — Strict cleaning
    # ================================================================
    # 2a. Construct Timestamp from Unix epoch column "time"
    df["Timestamp"] = pd.to_datetime(df["time"], unit="s", errors="coerce")
    df.dropna(subset=["Timestamp"], inplace=True)

    # 2b. Compute average latency from svr1–svr4 (exclude 1000 = timeout sentinel)
    svr_cols = ["svr1", "svr2", "svr3", "svr4"]
    svr_valid = df[svr_cols].replace(1000.0, np.nan)
    df["Avg-RTT"] = svr_valid.mean(axis=1)

    # 2c. Remove rows with invalid GPS sentinels
    gps_sentinel = df["latitude"].abs().gt(90) | df["longitude"].abs().gt(180)
    df = df[~gps_sentinel].copy()

    # 2d. Melbourne / Brimbank bounding box
    geo_mask = (
        df["latitude"].between(LAT_MIN, LAT_MAX)
        & df["longitude"].between(LON_MIN, LON_MAX)
    )
    df = df[geo_mask].copy()

    # 2e. Drop rows where all svr values were timeout
    df.dropna(subset=["Avg-RTT"], inplace=True)

    # 2f. Remove negative bitrates
    for col in ["Bitrate", "Bitrate-RX"]:
        if col in df.columns:
            df = df[df[col].notna() & (df[col] >= 0)].copy()

    # 2g. Drop rows with missing truck or square_id
    df.dropna(subset=["truck", "square_id"], inplace=True)

    print(f"Rows before cleaning: {rows_before:,}")
    print(f"Rows after cleaning : {len(df):,}")
    print(f"Rows removed        : {rows_before - len(df):,}")

    # ================================================================
    # Step 3 — Regular time-series resampling (1 s per session)
    # ================================================================
    df.sort_values(["truck", "square_id", "Timestamp"], inplace=True)
    df["_gap"] = df.groupby(["truck", "square_id"])["Timestamp"].diff()
    df["_session"] = (
        df.groupby(["truck", "square_id"])["_gap"]
          .transform(lambda s: (s > pd.Timedelta(seconds=MAX_GAP_S))
                                .fillna(True).cumsum())
    )
    df.drop(columns=["_gap"], inplace=True)

    _no_interp = {"square_id", "ue_id", "_session"}
    _num_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                 if c not in _no_interp]
    _fill_cols = [c for c in df.columns if c not in _num_cols and c != "Timestamp"]

    def _resample_session(g: pd.DataFrame) -> pd.DataFrame:
        g = g.set_index("Timestamp").resample("1s").first()
        fills = [c for c in _fill_cols if c in g.columns]
        nums = [c for c in _num_cols if c in g.columns]
        if fills:
            g[fills] = g[fills].ffill()
        if nums:
            g[nums] = g[nums].interpolate(method="linear", limit=MAX_GAP_S)
        return g

    rows_pre = len(df)
    df = (
        df.groupby(["truck", "square_id", "_session"], group_keys=False)
          .apply(_resample_session)
          .reset_index()
    )
    df.drop(columns=["_session"], inplace=True, errors="ignore")

    key_cols = [c for c in ["Bitrate-RX", "Avg-RTT"] if c in df.columns]
    if key_cols:
        df.dropna(subset=key_cols, how="all", inplace=True)

    print(f"Rows before resampling: {rows_pre:,}")
    print(f"Rows after resampling : {len(df):,}")

    # ================================================================
    # Step 4 — Dtype optimisation
    # ================================================================
    df = _optimise_dtypes(df)

    # ================================================================
    # Step 5 — Feature engineering
    # ================================================================

    # 5a. Temporal features
    df["hour"] = df["Timestamp"].dt.hour
    df["dow"] = df["Timestamp"].dt.dayofweek
    df["is_weekend"] = (df["dow"] >= 5).astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["dow"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dow"] / 7)
    df["is_work_hour"] = ((df["dow"] < 5) & df["hour"].between(8, 17)).astype(int)

    # 5b. Network / telecom features
    df["upload_mbps"] = pd.to_numeric(df["Bitrate"], errors="coerce")
    df["download_mbps"] = pd.to_numeric(df["Bitrate-RX"], errors="coerce")
    df["avg_latency"] = df["Avg-RTT"]

    # Retransmission rate
    if "Retransmissions" in df.columns and "Transfer size" in df.columns:
        retrans = pd.to_numeric(df["Retransmissions"], errors="coerce").fillna(0)
        xfer = pd.to_numeric(df["Transfer size"], errors="coerce").replace(0, np.nan)
        df["retransmission_rate"] = (retrans / xfer).fillna(0).clip(0, 1)
    elif "Retransmissions" in df.columns:
        retrans = pd.to_numeric(df["Retransmissions"], errors="coerce").fillna(0)
        max_retrans = retrans.quantile(0.99)
        df["retransmission_rate"] = (retrans / max_retrans).clip(0, 1) if max_retrans > 0 else 0.0
    else:
        df["retransmission_rate"] = 0.0

    # CWND features
    if "CWnd" in df.columns:
        df["cwnd"] = pd.to_numeric(df["CWnd"], errors="coerce").fillna(0)
        df["cwnd_squared"] = df["cwnd"] ** 2
    else:
        df["cwnd"] = 0.0
        df["cwnd_squared"] = 0.0

    # Server-level latency features
    svr_num_cols = [c for c in df.columns if c.startswith("svr") and c[3:].isdigit()]
    if len(svr_num_cols) >= 2:
        svr_valid_fe = df[svr_num_cols].replace(1000.0, np.nan)
        df["latency_spread"] = svr_valid_fe.max(axis=1) - svr_valid_fe.min(axis=1)
        df["latency_std"] = svr_valid_fe.std(axis=1)
        df["latency_spread"].fillna(0, inplace=True)
        df["latency_std"].fillna(0, inplace=True)
    else:
        df["latency_spread"] = 0.0
        df["latency_std"] = 0.0

    # Congestion indicator
    lat_75 = df["avg_latency"].quantile(0.75)
    dl_25 = df["download_mbps"].quantile(0.25)
    df["congestion_indicator"] = (
        (df["avg_latency"] > lat_75) & (df["download_mbps"] < dl_25)
    ).astype(int)

    # Interaction features
    df["latency_x_retrans"] = df["avg_latency"] * df["retransmission_rate"]
    df["cwnd_x_speed"] = df["cwnd"] * df["download_mbps"]
    df["download_x_latency"] = df["download_mbps"] * df["avg_latency"]

    # Ratio features
    df["cwnd_to_latency"] = df["cwnd"] / df["avg_latency"].replace(0, np.nan)
    df["download_to_upload"] = df["download_mbps"] / df["upload_mbps"].replace(0, np.nan)
    df["cwnd_to_latency"].fillna(0, inplace=True)
    df["download_to_upload"].fillna(0, inplace=True)

    # Jitter proxy
    df.sort_values(["truck", "square_id", "Timestamp"], inplace=True)
    df["jitter"] = (
        df.groupby(["truck", "square_id"])["avg_latency"]
          .diff().abs().fillna(0)
    )

    # 5c. Outlier detection & capping (1st / 99th percentile)
    outlier_cols = ["upload_mbps", "download_mbps", "avg_latency",
                    "retransmission_rate", "cwnd"]
    for col in outlier_cols:
        if col not in df.columns:
            continue
        p01 = df[col].quantile(0.01)
        p99 = df[col].quantile(0.99)
        outlier_mask = ~df[col].between(p01, p99)
        df[f"{col}_outlier"] = outlier_mask.astype(int)
        df[col] = df[col].clip(lower=p01, upper=p99)

    # 5d. Lag & rolling features (per truck + square_id)
    df.sort_values(["truck", "square_id", "Timestamp"], inplace=True)
    group_cols = ["truck", "square_id"]

    for tgt in ["download_mbps", "avg_latency", "upload_mbps"]:
        grp = df.groupby(group_cols)[tgt]
        for lag in [1, 2, 3]:
            df[f"{tgt}_lag{lag}"] = grp.shift(lag)

    for tgt in ["download_mbps", "avg_latency"]:
        grp = df.groupby(group_cols)[tgt]
        df[f"{tgt}_roll5_mean"] = grp.transform(
            lambda s: s.rolling(5, min_periods=1).mean()
        )
        df[f"{tgt}_roll5_std"] = grp.transform(
            lambda s: s.rolling(5, min_periods=1).std()
        )

    # Log-transform throughput
    df["log_download"] = np.log1p(df["download_mbps"])

    # Back-fill lag NaNs at group boundaries
    lag_fill_cols = [c for c in df.columns if "_lag" in c]
    for col in lag_fill_cols:
        df[col] = df.groupby(group_cols)[col].transform(lambda s: s.bfill())

    roll_std_cols = [c for c in df.columns if "_roll5_std" in c]
    df[roll_std_cols] = df[roll_std_cols].fillna(0)

    # 5e. Feature selection — drop highly-correlated (>0.95) features
    numeric_feats = df.select_dtypes(include=[np.number]).columns.tolist()
    exclude = {"square_id", "dataset"}
    feat_cols = [c for c in numeric_feats if c not in exclude]

    corr_mat = df[feat_cols].corr().abs()
    upper = corr_mat.where(np.triu(np.ones(corr_mat.shape, dtype=bool), k=1))
    to_drop: set[str] = set()
    for col in upper.columns:
        high = upper.index[upper[col] > CORR_THRESHOLD].tolist()
        if high:
            to_drop.add(col)

    print(f"Dropping {len(to_drop)} features with |r| > {CORR_THRESHOLD}")
    df.drop(columns=list(to_drop), inplace=True, errors="ignore")

    # 5f. Geospatial — distance to Melbourne CBD
    lat1 = np.radians(df["latitude"].values.astype(float))
    lon1 = np.radians(df["longitude"].values.astype(float))
    lat2 = np.radians(CBD_LAT)
    lon2 = np.radians(CBD_LON)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    df["dist_to_cbd_km"] = 2 * 6371 * np.arcsin(np.sqrt(a))

    # 5g. Train / validation temporal split (80 / 20 per truck)
    df.sort_values(["truck", "Timestamp"], inplace=True)
    splits = []
    for _, g in df.groupby("truck"):
        n = len(g)
        cutoff = int(n * 0.8)
        s = pd.Series("train", index=g.index)
        s.iloc[cutoff:] = "val"
        splits.append(s)
    df["dataset"] = pd.concat(splits)

    # ================================================================
    # Step 6 — Export
    # ================================================================
    out_path = output_dir / "cleaned_5g_data.csv"
    df.to_csv(out_path, index=False)
    print(f"✓ Saved {out_path}  ({len(df):,} rows × {len(df.columns)} cols)")


if __name__ == "__main__":
    main()

