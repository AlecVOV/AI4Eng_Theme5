# TASK: Add Winsorization (99th Percentile Capping) to Forecasting Pipeline

## Context
The current forecasting pipeline has no outlier handling. target_latency reaches 969.5 ms
(mean=130, so that's a 7x+ deviation) and target_throughput reaches 117.9 Mbps (mean=29.8).
These extreme values distort LSTM training via MSE loss.

We use **winsorization** — capping values at the 99th percentile — rather than dropping rows,
because this is time-series data and we cannot remove observations without breaking temporal
continuity.

## Requirements

### 1. Compute caps from TRAINING DATA ONLY
This is critical — using the full dataset to compute percentiles leaks test information.

```python
# After train/test split, BEFORE any scaling or model training
# Compute caps from training set only
PERCENTILE = 0.99

latency_cap = train_df['target_latency'].quantile(PERCENTILE)
throughput_cap = train_df['target_throughput'].quantile(PERCENTILE)

print(f"Latency cap (99th pct of train): {latency_cap:.2f} ms")
print(f"Throughput cap (99th pct of train): {throughput_cap:.2f} Mbps")
```

### 2. Apply caps to ALL latency/throughput columns consistently
The target columns AND their corresponding lag/rolling features must all be capped
at the same threshold. Otherwise the model sees uncapped inputs but capped targets.

```python
# Columns to cap with latency threshold
latency_cols = [
    'svr1',                    # raw latency feature
    'target_latency',          # prediction target
    'latency_lag_1h',          # lag features
    'latency_lag_2h',
    'latency_lag_3h',
    'latency_rolling_3h',      # rolling features
    'latency_rolling_6h',
]

# Columns to cap with throughput threshold
throughput_cols = [
    'upload_bitrate_mbps',
    'download_bitrate_mbps',
    'target_throughput',
    'throughput_lag_1h',
    'throughput_lag_2h',
    'throughput_lag_3h',
    'throughput_rolling_3h',
    'throughput_rolling_6h',
]

# Apply to BOTH train and test using caps derived from train only
for col in latency_cols:
    if col in train_df.columns:
        train_df[col] = train_df[col].clip(upper=latency_cap)
    if col in test_df.columns:
        test_df[col] = test_df[col].clip(upper=latency_cap)

for col in throughput_cols:
    if col in train_df.columns:
        train_df[col] = train_df[col].clip(upper=throughput_cap)
    if col in test_df.columns:
        test_df[col] = test_df[col].clip(upper=throughput_cap)
```

### 3. Apply BEFORE cluster-level aggregation if possible
If the pipeline aggregates per-zone data into cluster-level time series BEFORE the
train/test split, then winsorize at the per-zone level first (before aggregation).
The aggregation (mean) will then be based on capped values.

If the pipeline splits AFTER aggregation, apply winsorization after the split as shown above.

### 4. Log the effect
```python
# Count how many values were clipped
for col in latency_cols:
    if col in original_train_df.columns:
        n_clipped = (original_train_df[col] > latency_cap).sum()
        if n_clipped > 0:
            print(f"  {col}: {n_clipped} values clipped ({n_clipped/len(original_train_df)*100:.1f}%)")
```

### 5. Do NOT winsorize these columns
- latitude, longitude (geographic, not performance)
- hour_of_day, day_of_week (categorical/temporal)
- hour_sin, hour_cos, dow_sin, dow_cos (cyclical encoding, bounded [-1, 1])
- speed (truck speed, not a network metric — and it wasn't used in forecasting features anyway)
- observation_hour (counter, not a measurement)

### 6. Re-run the full pipeline after winsorization
Re-train both ARIMA and LSTM models. Save new predictions and metrics.
Compare winsorized vs non-winsorized results.

### 7. Output
Save these additional files:
- `winsorization_summary.csv` — cap values used, number of clipped values per column
- Updated prediction CSVs with `_winsorized` suffix
- Updated metrics in `all_forecasting_metrics.csv` (add rows for winsorized models or add a column)
- Updated forecast plots showing before/after comparison

## Pipeline Order (where winsorization fits)

```
1. Load clustering_data.csv and forecasting_data.csv
2. Run clustering (K-Means) → assign cluster labels
3. Merge cluster labels into forecasting data
4. Aggregate to cluster-level hourly time series
5. Train/test split (temporal: train ≤ July 18, test ≥ July 19)
6. >>> WINSORIZE HERE <<< (compute caps from train, apply to both)
7. ARIMA training and prediction
8. LSTM scaling, windowing, training, and prediction
9. Evaluation metrics and plots
```

## Expected Impact
- LSTM training should be more stable (fewer loss spikes from extreme values)
- ARIMA might not change much (it already predicts a flat line)
- MAPE should improve noticeably since extreme values inflate percentage errors
- The forecast plots should show fewer wild spikes in the actual values
