"""
5G Network Performance Data — Full Preprocessing Pipeline
=========================================================
Run this locally on your machine (not in Claude chat).

USAGE:
  Step 1: Run discovery mode first to check your raw column names
      python preprocess_5g.py --discover /path/to/data/folder

  Step 2: Once you've verified the column mapping, run full processing
      python preprocess_5g.py /path/to/data/folder

  If your data is a single combined CSV instead of a folder of CSVs:
      python preprocess_5g.py --single /path/to/combined.csv

OUTPUT FILES (saved to same directory as this script):
  - cleaned_base.csv          — full cleaned dataset with engineered features
  - zones_for_clustering.csv  — one row per zone (square_id), ready for K-Means/DBSCAN
  - timeseries_for_forecasting.csv — one row per zone per hour, ready for ARIMA/LSTM
  - preprocessing_report.txt  — summary stats and data quality info
"""

import pandas as pd
import numpy as np
import os
import sys
import glob
from pathlib import Path


# =============================================================================
# COLUMN MAPPING — ADJUST THIS IF YOUR RAW COLUMNS HAVE DIFFERENT NAMES
# =============================================================================
# Run with --discover first to see your actual column names, then edit if needed.

COLUMN_MAP = {
    # Raw column name (left) → Standardized name (right)
    # If your raw columns already match the right side, leave as-is.
    "latitude": "latitude",
    "longitude": "longitude",
    "speed": "speed",
    "svr1": "svr1",
    "svr2": "svr2",
    "svr3": "svr3",
    "svr4": "svr4",
    "upload_transfer_size_mbytes": "upload_transfer_size_mbytes",
    "upload_bitrate_mbits_sec": "upload_bitrate_mbits_sec",
    "download_transfer_size_rx_mbytes": "download_transfer_size_rx_mbytes",
    "download_bitrate_rx_mbits_sec": "download_bitrate_rx_mbits_sec",
    "application_data": "application_data",
    "send_data": "send_data",
    "square_id": "square_id",
    # Datetime — could be 'time' (unix), 'datetime', or separate date/time columns.
    # The script will try to auto-detect. If it fails, edit the parse_datetime() function.
}


# =============================================================================
# DATA LOADING
# =============================================================================

def load_data(path, single_file=False):
    """Load all CSVs from a folder, or a single CSV file."""
    if single_file:
        print(f"Loading single file: {path}")
        df = pd.read_csv(path, low_memory=False)
        print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
        return df

    csv_files = sorted(glob.glob(os.path.join(path, "*.csv")))
    if not csv_files:
        print(f"ERROR: No CSV files found in {path}")
        sys.exit(1)

    print(f"Found {len(csv_files)} CSV files in {path}")
    frames = []
    for i, f in enumerate(csv_files):
        try:
            chunk = pd.read_csv(f, low_memory=False)
            frames.append(chunk)
            if (i + 1) % 10 == 0 or i == 0:
                print(f"  Loaded {i+1}/{len(csv_files)}: {os.path.basename(f)} ({len(chunk):,} rows)")
        except Exception as e:
            print(f"  WARNING: Skipping {os.path.basename(f)} — {e}")

    df = pd.concat(frames, ignore_index=True)
    print(f"Total: {len(df):,} rows, {len(df.columns)} columns")
    return df


def discover_columns(df):
    """Print column info so user can verify the mapping."""
    print("\n" + "=" * 60)
    print("COLUMN DISCOVERY")
    print("=" * 60)
    print(f"\nFound {len(df.columns)} columns:\n")
    for i, col in enumerate(df.columns):
        dtype = df[col].dtype
        non_null = df[col].notna().sum()
        sample_vals = df[col].dropna().head(3).tolist()
        print(f"  [{i:2d}] {col:<45} dtype={str(dtype):<10} non-null={non_null:,}  samples={sample_vals}")

    print("\n" + "=" * 60)
    print("CHECK: Do these columns match the COLUMN_MAP in the script?")
    print("If not, edit COLUMN_MAP before running the full pipeline.")
    print("=" * 60)


# =============================================================================
# CLEANING
# =============================================================================

def parse_datetime(df):
    """
    Try to find/create a proper datetime column.
    Attempts in order:
      1. Column named 'datetime' already exists
      2. Column named 'time' with unix timestamps
      3. Separate 'date' + 'time' columns
    """
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        print("  Parsed existing 'datetime' column")
    elif "time" in df.columns:
        # Check if it looks like unix timestamp (large integers)
        sample = df["time"].dropna().iloc[0] if len(df["time"].dropna()) > 0 else None
        if sample and (isinstance(sample, (int, float)) and sample > 1e9):
            df["datetime"] = pd.to_datetime(df["time"], unit="s", errors="coerce")
            print("  Converted unix 'time' column to datetime")
        else:
            df["datetime"] = pd.to_datetime(df["time"], errors="coerce")
            print("  Parsed 'time' column as datetime string")
    elif "date" in df.columns:
        # Try combining date + time columns
        time_col = [c for c in df.columns if c.lower() in ("time", "hour", "timestamp")]
        if time_col:
            df["datetime"] = pd.to_datetime(
                df["date"].astype(str) + " " + df[time_col[0]].astype(str),
                errors="coerce"
            )
            print(f"  Combined 'date' + '{time_col[0]}' into datetime")
        else:
            df["datetime"] = pd.to_datetime(df["date"], errors="coerce")
            print("  Parsed 'date' column as datetime")
    else:
        print("  WARNING: No datetime column found. Check your data manually.")
        print(f"  Available columns: {list(df.columns)}")
        df["datetime"] = pd.NaT

    return df


def clean_data(df):
    """Apply all cleaning steps."""
    initial_rows = len(df)
    report = []
    report.append(f"Initial rows: {initial_rows:,}")

    # 1. Rename columns if needed
    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in df.columns and k != v}
    if rename_map:
        df = df.rename(columns=rename_map)
        print(f"  Renamed {len(rename_map)} columns")

    # 2. Parse datetime
    df = parse_datetime(df)

    # 3. Filter invalid GPS coordinates (99,999 = invalid per project spec)
    if "latitude" in df.columns and "longitude" in df.columns:
        gps_invalid = (
            (df["latitude"].abs() > 90) |
            (df["longitude"].abs() > 180) |
            (df["latitude"] == 99999) | (df["latitude"] == 99.999) |
            (df["longitude"] == 99999) | (df["longitude"] == 99.999) |
            (df["latitude"].isna()) |
            (df["longitude"].isna())
        )
        n_invalid_gps = gps_invalid.sum()
        df = df[~gps_invalid].copy()
        print(f"  Removed {n_invalid_gps:,} rows with invalid GPS ({n_invalid_gps/initial_rows*100:.1f}%)")
        report.append(f"Invalid GPS rows removed: {n_invalid_gps:,}")

    # 4. Filter rows with missing latency data (need at least some server values)
    svr_cols = [c for c in ["svr1", "svr2", "svr3", "svr4"] if c in df.columns]
    if svr_cols:
        all_svr_null = df[svr_cols].isna().all(axis=1)
        n_no_latency = all_svr_null.sum()
        df = df[~all_svr_null].copy()
        print(f"  Removed {n_no_latency:,} rows with all latency values missing")
        report.append(f"All-null latency rows removed: {n_no_latency:,}")

    # 5. Drop rows missing square_id (can't assign to a zone)
    if "square_id" in df.columns:
        n_no_zone = df["square_id"].isna().sum()
        df = df.dropna(subset=["square_id"]).copy()
        print(f"  Removed {n_no_zone:,} rows with missing square_id")
        report.append(f"Missing square_id rows removed: {n_no_zone:,}")

    final_rows = len(df)
    print(f"  Cleaning complete: {initial_rows:,} → {final_rows:,} rows ({initial_rows - final_rows:,} removed)")
    report.append(f"Final rows after cleaning: {final_rows:,}")
    report.append(f"Total rows removed: {initial_rows - final_rows:,} ({(initial_rows - final_rows)/initial_rows*100:.1f}%)")

    return df, report


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

def engineer_features(df):
    """Create derived features matching the approach from the sample."""
    svr_cols = [c for c in ["svr1", "svr2", "svr3", "svr4"] if c in df.columns]

    if svr_cols:
        df["average_latency"] = df[svr_cols].mean(axis=1)
        df["latency_std"] = df[svr_cols].std(axis=1)
        df["max_latency"] = df[svr_cols].max(axis=1)
        df["min_latency"] = df[svr_cols].min(axis=1)
        print(f"  Latency features from {len(svr_cols)} server columns")

    if "upload_bitrate_mbits_sec" in df.columns and "download_bitrate_rx_mbits_sec" in df.columns:
        df["total_throughput"] = df["upload_bitrate_mbits_sec"] + df["download_bitrate_rx_mbits_sec"]
        print("  Created total_throughput")

    if "upload_transfer_size_mbytes" in df.columns and "download_transfer_size_rx_mbytes" in df.columns:
        df["total_transfer"] = df["upload_transfer_size_mbytes"] + df["download_transfer_size_rx_mbytes"]
        print("  Created total_transfer")

    if "upload_bitrate_mbits_sec" in df.columns and "download_bitrate_rx_mbits_sec" in df.columns:
        # Avoid division by zero
        df["upload_download_ratio"] = df["upload_bitrate_mbits_sec"] / df["download_bitrate_rx_mbits_sec"].replace(0, np.nan)
        print("  Created upload_download_ratio")

    if "datetime" in df.columns:
        df["day_of_week"] = df["datetime"].dt.day_name()
        df["hour_of_day"] = df["datetime"].dt.hour
        df["date"] = df["datetime"].dt.date
        print("  Extracted day_of_week, hour_of_day, date")

    return df


# =============================================================================
# AGGREGATION — CLUSTERING (per zone)
# =============================================================================

def aggregate_for_clustering(df):
    """
    One row per square_id. Summarizes all observations in that zone.
    This is what goes into K-Means / DBSCAN.
    """
    agg_dict = {}

    # GPS centroid
    if "latitude" in df.columns:
        agg_dict["latitude"] = ("latitude", "mean")
        agg_dict["longitude"] = ("longitude", "mean")

    # Latency stats
    if "average_latency" in df.columns:
        agg_dict["mean_latency"] = ("average_latency", "mean")
        agg_dict["std_latency"] = ("average_latency", "std")
        agg_dict["median_latency"] = ("average_latency", "median")

    # Throughput stats
    if "total_throughput" in df.columns:
        agg_dict["mean_throughput"] = ("total_throughput", "mean")
        agg_dict["std_throughput"] = ("total_throughput", "std")
        agg_dict["median_throughput"] = ("total_throughput", "median")

    # Transfer stats
    if "total_transfer" in df.columns:
        agg_dict["mean_transfer"] = ("total_transfer", "mean")

    # Upload/download ratio
    if "upload_download_ratio" in df.columns:
        agg_dict["mean_ul_dl_ratio"] = ("upload_download_ratio", "mean")

    # Speed (truck speed — could correlate with measurement quality)
    if "speed" in df.columns:
        agg_dict["mean_speed"] = ("speed", "mean")

    # Observation count (useful for filtering low-data zones)
    agg_dict["observation_count"] = ("average_latency", "count")

    zones = df.groupby("square_id").agg(**agg_dict).reset_index()

    # Fill any NaN std values (zones with single observation)
    for col in zones.columns:
        if "std" in col:
            zones[col] = zones[col].fillna(0)

    print(f"  Clustering dataset: {len(zones)} zones")
    print(f"  Observations per zone: min={zones['observation_count'].min()}, "
          f"max={zones['observation_count'].max()}, "
          f"median={zones['observation_count'].median():.0f}")

    return zones


# =============================================================================
# AGGREGATION — FORECASTING (per zone per hour)
# =============================================================================

def aggregate_for_forecasting(df):
    """
    One row per square_id per hour. Preserves temporal ordering.
    This is what goes into ARIMA / LSTM.
    """
    if "datetime" not in df.columns or df["datetime"].isna().all():
        print("  ERROR: Cannot create time-series aggregation — no valid datetime column")
        return pd.DataFrame()

    # Create hourly bin
    df = df.copy()
    df["datetime_hour"] = df["datetime"].dt.floor("h")

    agg_dict = {}

    if "average_latency" in df.columns:
        agg_dict["mean_latency"] = ("average_latency", "mean")
    if "total_throughput" in df.columns:
        agg_dict["mean_throughput"] = ("total_throughput", "mean")
    if "total_transfer" in df.columns:
        agg_dict["mean_transfer"] = ("total_transfer", "mean")
    if "upload_download_ratio" in df.columns:
        agg_dict["mean_ul_dl_ratio"] = ("upload_download_ratio", "mean")
    if "speed" in df.columns:
        agg_dict["mean_speed"] = ("speed", "mean")
    if "latitude" in df.columns:
        agg_dict["latitude"] = ("latitude", "mean")
        agg_dict["longitude"] = ("longitude", "mean")

    agg_dict["observation_count"] = ("average_latency", "count")

    ts = df.groupby(["square_id", "datetime_hour"]).agg(**agg_dict).reset_index()

    # Add time features
    ts["hour_of_day"] = ts["datetime_hour"].dt.hour
    ts["day_of_week"] = ts["datetime_hour"].dt.dayofweek  # 0=Monday
    ts["date"] = ts["datetime_hour"].dt.date

    # Sort by zone then time (important for time-series models)
    ts = ts.sort_values(["square_id", "datetime_hour"]).reset_index(drop=True)

    n_zones = ts["square_id"].nunique()
    n_hours = ts["datetime_hour"].nunique()
    print(f"  Forecasting dataset: {len(ts)} rows ({n_zones} zones × up to {n_hours} time windows)")
    print(f"  Date range: {ts['datetime_hour'].min()} to {ts['datetime_hour'].max()}")

    return ts


# =============================================================================
# REPORTING
# =============================================================================

def write_report(df, zones, ts, clean_report, output_dir):
    """Write a summary of the preprocessing for the project report."""
    report_path = os.path.join(output_dir, "preprocessing_report.txt")
    with open(report_path, "w") as f:
        f.write("5G Network Performance — Preprocessing Report\n")
        f.write("=" * 50 + "\n\n")

        f.write("DATA CLEANING\n")
        f.write("-" * 30 + "\n")
        for line in clean_report:
            f.write(f"  {line}\n")

        f.write(f"\nCLEANED BASE DATASET\n")
        f.write("-" * 30 + "\n")
        f.write(f"  Rows: {len(df):,}\n")
        f.write(f"  Columns: {len(df.columns)}\n")
        f.write(f"  Unique zones (square_id): {df['square_id'].nunique()}\n")
        if "datetime" in df.columns and df["datetime"].notna().any():
            f.write(f"  Date range: {df['datetime'].min()} to {df['datetime'].max()}\n")
        if "average_latency" in df.columns:
            f.write(f"  Average latency: mean={df['average_latency'].mean():.2f}, "
                    f"std={df['average_latency'].std():.2f}, "
                    f"min={df['average_latency'].min():.2f}, "
                    f"max={df['average_latency'].max():.2f}\n")
        if "total_throughput" in df.columns:
            f.write(f"  Total throughput: mean={df['total_throughput'].mean():.2f}, "
                    f"std={df['total_throughput'].std():.2f}, "
                    f"min={df['total_throughput'].min():.2f}, "
                    f"max={df['total_throughput'].max():.2f}\n")

        f.write(f"\nCLUSTERING DATASET (zones_for_clustering.csv)\n")
        f.write("-" * 30 + "\n")
        f.write(f"  Zones: {len(zones)}\n")
        f.write(f"  Columns: {list(zones.columns)}\n")
        if "observation_count" in zones.columns:
            f.write(f"  Observations per zone: min={zones['observation_count'].min()}, "
                    f"median={zones['observation_count'].median():.0f}, "
                    f"max={zones['observation_count'].max()}\n")

        f.write(f"\nFORECASTING DATASET (timeseries_for_forecasting.csv)\n")
        f.write("-" * 30 + "\n")
        f.write(f"  Rows: {len(ts):,}\n")
        f.write(f"  Columns: {list(ts.columns)}\n")
        if len(ts) > 0:
            f.write(f"  Zones: {ts['square_id'].nunique()}\n")
            f.write(f"  Time windows: {ts['datetime_hour'].nunique()}\n")

    print(f"\n  Report saved to {report_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Parse arguments
    single_file = False
    discover_only = False
    path = sys.argv[-1]

    if "--discover" in sys.argv:
        discover_only = True
    if "--single" in sys.argv:
        single_file = True

    # Output directory = same folder as this script
    output_dir = os.path.dirname(os.path.abspath(__file__)) or "."

    # Load data
    print("\n[1/5] LOADING DATA")
    print("-" * 40)
    df = load_data(path, single_file=single_file)

    # Discovery mode — just print columns and exit
    if discover_only:
        discover_columns(df)
        return

    # Clean
    print("\n[2/5] CLEANING")
    print("-" * 40)
    df, clean_report = clean_data(df)

    # Engineer features
    print("\n[3/5] FEATURE ENGINEERING")
    print("-" * 40)
    df = engineer_features(df)

    # Save cleaned base (optional — comment out if too large)
    base_path = os.path.join(output_dir, "cleaned_base.csv")
    print(f"\n  Saving cleaned base to {base_path}...")
    df.to_csv(base_path, index=False)
    size_mb = os.path.getsize(base_path) / (1024 * 1024)
    print(f"  Saved ({size_mb:.1f} MB)")

    # Aggregate for clustering
    print("\n[4/5] AGGREGATING FOR CLUSTERING")
    print("-" * 40)
    zones = aggregate_for_clustering(df)
    zones_path = os.path.join(output_dir, "zones_for_clustering.csv")
    zones.to_csv(zones_path, index=False)
    print(f"  Saved to {zones_path}")

    # Aggregate for forecasting
    print("\n[5/5] AGGREGATING FOR FORECASTING")
    print("-" * 40)
    ts = aggregate_for_forecasting(df)
    ts_path = os.path.join(output_dir, "timeseries_for_forecasting.csv")
    ts.to_csv(ts_path, index=False)
    print(f"  Saved to {ts_path}")

    # Write report
    write_report(df, zones, ts, clean_report, output_dir)

    print("\n" + "=" * 50)
    print("DONE. Output files:")
    print(f"  1. {base_path}")
    print(f"  2. {zones_path}")
    print(f"  3. {ts_path}")
    print(f"  4. {os.path.join(output_dir, 'preprocessing_report.txt')}")
    print("\nNext: Upload zones_for_clustering.csv and timeseries_for_forecasting.csv")
    print("to Claude Code or Claude chat for modeling.")
    print("=" * 50)


if __name__ == "__main__":
    main()
