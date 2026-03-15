# Verification Report: 5G Network Performance — Clustering & Forecasting

**Generated:** 2026-03-12
**Pipeline script:** `run_verification.py`
**Data source:** `clustering_data.csv` (297 zones), `forecasting_data.csv` (5,641 hourly records)

---

## How to Verify This Report

All intermediate data, predictions, and metrics are saved as CSV files in this folder. To verify any claim below:

1. **Read the CSV** referenced in each section
2. **Recompute the metric** from the raw prediction files
3. **Cross-check** against the full run log (`full_run_log.txt`)

---

## Phase 0: Data Quality

### Files to check:
- `data_summary/clustering_data_describe.csv` — statistical summary of clustering input
- `data_summary/forecasting_data_describe.csv` — statistical summary of forecasting input
- `data_summary/clustering_data_head20.csv` — first 20 rows of clustering data
- `data_summary/forecasting_data_head20.csv` — first 20 rows of forecasting data

### Claims to verify:
| Claim | How to verify |
|-------|---------------|
| clustering_data.csv has 297 rows x 8 columns | Check `clustering_data_describe.csv` count row |
| forecasting_data.csv has 5,641 rows x 29 columns | Check `forecasting_data_describe.csv` count row |
| Zero NaN values in both datasets | Both describe files should show equal counts across all columns |
| Forecasting data has lag features (1h, 2h, 3h) | Check column names in `forecasting_data_head20.csv` |
| Forecasting data has rolling averages (3h, 6h) | Check column names in `forecasting_data_head20.csv` |
| Forecasting data has cyclical encoding (sin/cos) | Check `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos` columns |
| Forecasting data has explicit target columns | Check `target_latency`, `target_throughput` columns |

---

## Phase 1: Clustering

### Step 1.1 — Filtering

**Decision:** Remove zones with `measurement_count < 50` (unreliable aggregate statistics).

**Result:** 297 → 257 zones (40 removed).

**File to check:** `clustering/zones_filtered.csv` — should have 257 rows, all with `measurement_count >= 50`.

### Step 1.2 — Feature Selection

**Features used:** `svr1`, `upload_bitrate_mbps`, `download_bitrate_mbps`, `latitude`, `longitude`

**Justification:**
- `svr1` = server latency (ms) — primary network quality metric
- `upload_bitrate_mbps` + `download_bitrate_mbps` = throughput — primary performance metrics
- `latitude` + `longitude` = geographic grouping (project explicitly asks about location-based zones)
- `speed` excluded (truck speed, not network metric)
- `measurement_count` excluded (property of data collection, not network performance)

### Step 1.3 — Feature Scaling

**Method:** StandardScaler (zero mean, unit variance)

**Verification:** Post-scaling, all features should have mean ≈ 0.0 and std ≈ 1.0. See `full_run_log.txt` section [1.3].

### Step 1.4 — Optimal K Selection

**File to check:** `clustering/k_selection_metrics.csv`

This file contains for each K (2–10):
- `inertia` — within-cluster sum of squares (lower = tighter clusters)
- `silhouette` — cluster separation quality (-1 to 1, higher = better)
- `davies_bouldin` — cluster overlap (lower = better)
- `calinski_harabasz` — ratio of between/within cluster variance (higher = better)
- `cluster_sizes` — number of zones per cluster

**Verification steps:**
1. Open `k_selection_metrics.csv`
2. Confirm K=2 has the highest silhouette score (0.2514)
3. Confirm inertia decreases monotonically as K increases
4. Check the elbow plot: `clustering/elbow_silhouette.png`

**Result:** K=2 selected (silhouette = 0.2514)

| K | Silhouette | Davies-Bouldin | Calinski-Harabasz |
|---|-----------|----------------|-------------------|
| 2 | **0.2514** | 1.5076 | **91.64** |
| 3 | 0.2172 | 1.4981 | 78.13 |
| 4 | 0.2337 | 1.3255 | 71.03 |
| 5 | 0.2461 | **1.2367** | 67.60 |

### Step 1.5 — K-Means Results

**File to check:** `clustering/zones_clustered.csv`

| Cluster | Name | Size | Mean Latency (svr1) | Mean Upload (Mbps) | Mean Download (Mbps) |
|---------|------|------|---------------------|--------------------|--------------------|
| 0 | Low Latency / High Throughput | 159 (61.9%) | 76.67 ms | 12.16 | 20.35 |
| 1 | High Latency / Low Throughput | 98 (38.1%) | 202.83 ms | 6.86 | 15.73 |

**Verification:**
1. Open `clustering/zones_clustered.csv`
2. Filter by `kmeans_cluster == 0`, compute mean of `svr1` → should be ≈ 76.67
3. Filter by `kmeans_cluster == 1`, compute mean of `svr1` → should be ≈ 202.83
4. Check that cluster profiles make intuitive sense (high latency correlates with low throughput)

**Detailed profiles:** `clustering/cluster_profiles_detailed.csv` (includes mean, std, min, max per cluster per feature)

### Step 1.6 — DBSCAN Comparison

**File to check:** `clustering/dbscan_parameter_search.csv`

**Best parameters:** eps=0.4, min_samples=3
**Result:** 5 clusters + 240 noise points (93.4% noise)

**Interpretation:** DBSCAN identifies that the data is largely continuous with a few small dense pockets. The high noise rate indicates most zones don't form tight density-based clusters — K-Means is the more appropriate method here.

### Step 1.7 — Evaluation Metrics

**File to check:** `clustering/clustering_metrics.json`

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Silhouette Score | 0.2514 | Moderate — clusters have some structure but overlap exists. Typical for real-world spatial data. |
| Davies-Bouldin Index | 1.5076 | Moderate — some cluster overlap. Lower is better. |
| Calinski-Harabasz Index | 91.64 | Good relative separation for K=2. Higher is better. |

**Per-cluster silhouette:** `clustering/per_cluster_silhouette.csv`

| Cluster | Mean Silhouette | % Negative | Interpretation |
|---------|----------------|------------|----------------|
| 0 | 0.2528 | 0.6% | Very few misclassified zones |
| 1 | 0.2490 | 0.0% | No misclassified zones |

### Clustering Plots

| File | Description | What to check |
|------|-------------|---------------|
| `clustering/elbow_silhouette.png` | Elbow method + silhouette vs K | Elbow visible around K=2-3, silhouette peaks at K=2 |
| `clustering/cluster_maps.png` | Geographic scatter (K-Means left, DBSCAN right) | Clusters should show geographic patterns |
| `clustering/cluster_profiles.png` | Bar chart of mean features per cluster | Cluster 0 should show lower svr1, higher throughput |
| `clustering/silhouette_plot.png` | Per-sample silhouette values | Both clusters should have mostly positive values |

---

## Phase 2: Forecasting

### Step 2.1 — Cluster-Based Approach

**Rationale:** Individual zone time series are too sparse (median zone = 13 hourly observations). By pooling zones within each cluster, we get denser series:
- Cluster 0: 157 hourly records
- Cluster 1: 134 hourly records

**File to check:** `forecasting/cluster_timeseries_aggregated.csv` — 291 rows total

### Step 2.2 — Temporal Train/Test Split

**Split point:** Train ≤ 2022-07-18, Test ≥ 2022-07-19

| Set | Rows | Date Range |
|-----|------|-----------|
| Train | 208 | 2022-07-03 19:00 to 2022-07-18 00:00 |
| Test | 65 | 2022-07-19 00:00 to 2022-07-22 02:00 |

**Files to check:** `forecasting/train_set_pre_winsorize.csv`, `forecasting/test_set_pre_winsorize.csv` (before capping), `forecasting/train_set.csv`, `forecasting/test_set.csv` (after capping)

**Verification:** Confirm no temporal leakage — all train dates < all test dates.

### Step 2.3 — Winsorization (99th Percentile Capping)

**Rationale:** `target_latency` reaches 969.5 ms (mean=130, a 7x+ deviation) and `target_throughput` reaches 117.9 Mbps. These extreme values distort LSTM training via MSE loss. We use winsorization (capping at 99th percentile) rather than dropping rows, because removing observations would break temporal continuity.

**Critical design decisions:**
1. Caps computed from **training data only** (no test data leakage)
2. Applied to **all related columns consistently** (targets + lags + rolling averages)
3. Applied **after** train/test split, **before** any model training

**Cap values (from training set 99th percentile):**
| Metric | Cap Value | Raw Max (train) | Raw Max (test) |
|--------|-----------|-----------------|----------------|
| Latency | 305.94 ms | 387.9 ms | — |
| Throughput | 107.91 Mbps | 113.5 Mbps | — |

**File to check:** `forecasting/winsorization_summary.csv`

This file contains per-column: cap value, number of values clipped in train and test, max before/after.

**Clipping summary:**

| Column | Train Clipped | Test Clipped | Notes |
|--------|--------------|-------------|-------|
| svr1 | 1 (0.5%) | 0 | Raw latency feature |
| target_latency | 3 (1.4%) | 0 | Prediction target |
| latency_lag_1h | 0 | 0 | Already below cap |
| latency_rolling_3h | 0 | 0 | Rolling averages smooth outliers |
| latency_rolling_6h | 0 | 0 | Rolling averages smooth outliers |
| upload_bitrate_mbps | 0 | 0 | Already below cap |
| download_bitrate_mbps | 0 | 0 | Already below cap |
| target_throughput | 3 (1.4%) | 1 (1.5%) | Prediction target |
| throughput_lag_1h | 1 (0.5%) | 0 | Lag feature |
| throughput_rolling_3h | 0 | 0 | Already below cap |
| throughput_rolling_6h | 0 | 0 | Already below cap |

**Columns NOT winsorized (by design):** latitude, longitude, hour_of_day, day_of_week, hour_sin, hour_cos, dow_sin, dow_cos, speed, observation_hour.

**Verification steps:**
1. Open `forecasting/winsorization_summary.csv` — confirm cap values match 305.94 and 107.91
2. Open `forecasting/train_set_pre_winsorize.csv` — confirm `target_latency` max > 305.94
3. Open `forecasting/train_set.csv` — confirm `target_latency` max <= 305.94
4. Confirm caps were derived from training data only (no test leakage)

### Step 2.4 — ARIMA Results (with winsorization)

**Target: Latency (target_latency)**

| Cluster | ARIMA Order | RMSE | MAE | MAPE |
|---------|------------|------|-----|------|
| 0 | (0,1,1) | 39.53 | 27.23 | 29.0% |
| 1 | (0,1,1) | 69.47 | 59.02 | 37.6% |

**Target: Throughput (target_throughput)**

| Cluster | ARIMA Order | RMSE | MAE | MAPE |
|---------|------------|------|-----|------|
| 0 | (0,0,2) | 15.23 | 8.96 | 18.7% |
| 1 | (0,1,1) | 5.93 | 4.61 | 17.9% |

**Verification files:**
- `forecasting/arima_target_latency_cluster0_predictions.csv` — actual vs predicted values
- `forecasting/arima_target_latency_cluster1_predictions.csv`
- `forecasting/arima_target_throughput_cluster0_predictions.csv`
- `forecasting/arima_target_throughput_cluster1_predictions.csv`

**How to verify RMSE:**
1. Open any prediction CSV (e.g., `arima_target_throughput_cluster1_predictions.csv`)
2. Compute: `sqrt(mean((actual - predicted)^2))`
3. Result should match the RMSE reported above

### Step 2.5 — LSTM Results (with winsorization)

**Architecture:** LSTM(32) -> Dropout(0.2) -> LSTM(16) -> Dropout(0.2) -> Dense(1)
**Window size:** 6 time steps
**Optimizer:** Adam, Loss: MSE
**Early stopping:** patience=10, restore_best_weights=True

**Target: Latency (target_latency)**

| Cluster | Features | Train/Test Seq | Epochs | Train Loss | Val Loss | RMSE | MAE | MAPE |
|---------|----------|---------------|--------|------------|----------|------|-----|------|
| 0 | svr1, lag_1h, roll_3h, roll_6h, hour_sin/cos, dow_sin/cos | 120/31 | 11 | 0.007901 | 0.041919 | 28.43 | 24.38 | 27.8% |
| 1 | svr1, lag_1h, roll_3h, roll_6h, hour_sin/cos, dow_sin/cos | 102/26 | 14 | 0.044925 | 0.066150 | 49.51 | 38.50 | 22.4% |

**Target: Throughput (target_throughput)**

| Cluster | Features | Train/Test Seq | Epochs | Train Loss | Val Loss | RMSE | MAE | MAPE |
|---------|----------|---------------|--------|------------|----------|------|-----|------|
| 0 | ul/dl_bitrate, lag_1h, roll_3h, roll_6h, hour_sin/cos, dow_sin/cos | 120/31 | 12 | 0.049042 | 0.017770 | 15.56 | 11.39 | 29.8% |
| 1 | ul/dl_bitrate, lag_1h, roll_3h, roll_6h, hour_sin/cos, dow_sin/cos | 102/26 | 76 | 0.050850 | 0.026275 | 5.77 | 4.24 | 16.1% |

**Verification files:**
- `forecasting/lstm_target_latency_cluster0_predictions.csv` — actual vs predicted
- `forecasting/lstm_target_latency_cluster0_training_history.csv` — epoch-by-epoch loss
- (same pattern for cluster1, and for throughput target)

**How to verify:**
1. Open any LSTM prediction CSV
2. Recompute RMSE, MAE, MAPE from actual/predicted columns
3. Open training history CSV — confirm loss decreases over epochs and early stopping triggered

### Step 2.6 — Model Comparison (with winsorization)

**File to check:** `forecasting/all_forecasting_metrics.csv` — complete table of all metrics for all models

| Target | Cluster | ARIMA RMSE | LSTM RMSE | Better | ARIMA MAPE | LSTM MAPE | Better |
|--------|---------|-----------|-----------|--------|------------|-----------|--------|
| target_latency | 0 | 39.53 | **28.43** | LSTM | 29.0% | **27.8%** | LSTM |
| target_latency | 1 | 69.47 | **49.51** | LSTM | 37.6% | **22.4%** | LSTM |
| target_throughput | 0 | **15.23** | 15.56 | ARIMA | **18.7%** | 29.8% | ARIMA |
| target_throughput | 1 | 5.93 | **5.77** | LSTM | 17.9% | **16.1%** | LSTM |

**Effect of winsorization on ARIMA (comparing to pre-winsorization run):**
| Target | Cluster | RMSE Before | RMSE After | Change |
|--------|---------|-------------|------------|--------|
| target_latency | 1 | 71.57 | 69.47 | -2.9% (improved) |
| target_throughput | 0 | 16.12 | 15.23 | -5.5% (improved) |

**Conclusion:** Winsorization improved ARIMA on Cluster 1 latency (RMSE 71.57 -> 69.47) and Cluster 0 throughput (RMSE 16.12 -> 15.23) by removing the influence of extreme outliers. LSTM remains the stronger model for latency prediction across both clusters. The winsorization had modest impact because only ~1-3 values per column exceeded the 99th percentile cap — the data was already mostly well-behaved after cluster-level aggregation.

### Forecast Plots

| File | Description |
|------|-------------|
| `forecasting/forecast_target_latency.png` | Actual vs predicted latency, both models, both clusters |
| `forecasting/forecast_target_throughput.png` | Actual vs predicted throughput, both models, both clusters |

---

## Complete File Inventory

### `verification_output/data_summary/`
| File | Contents |
|------|----------|
| `clustering_data_describe.csv` | pandas describe() of clustering input |
| `forecasting_data_describe.csv` | pandas describe() of forecasting input |
| `clustering_data_head20.csv` | First 20 rows of clustering data |
| `forecasting_data_head20.csv` | First 20 rows of forecasting data |

### `verification_output/clustering/`
| File | Contents |
|------|----------|
| `zones_filtered.csv` | 257 zones after measurement_count >= 50 filter |
| `zones_clustered.csv` | 257 zones with `kmeans_cluster` and `dbscan_cluster` labels |
| `k_selection_metrics.csv` | Silhouette, DB, CH for K=2..10 |
| `dbscan_parameter_search.csv` | All DBSCAN eps/min_samples combinations tested |
| `cluster_profiles_detailed.csv` | Mean/std/min/max of features per cluster |
| `per_cluster_silhouette.csv` | Per-cluster silhouette statistics |
| `clustering_metrics.json` | Final metrics in JSON format |
| `elbow_silhouette.png` | Elbow + silhouette plot |
| `cluster_maps.png` | Geographic scatter plot |
| `cluster_profiles.png` | Feature bar charts per cluster |
| `silhouette_plot.png` | Per-sample silhouette visualization |

### `verification_output/forecasting/`
| File | Contents |
|------|----------|
| `cluster_timeseries_aggregated.csv` | Pooled cluster-level hourly time series (pre-winsorization) |
| `cluster_timeseries_winsorized.csv` | Cluster time series after winsorization |
| `winsorization_summary.csv` | Cap values, clipped counts per column, max before/after |
| `train_set_pre_winsorize.csv` | Training data before winsorization |
| `test_set_pre_winsorize.csv` | Test data before winsorization |
| `train_set.csv` | Training data after winsorization |
| `test_set.csv` | Test data after winsorization |
| `all_forecasting_metrics.csv` | Complete metrics table for all models |
| `arima_*_predictions.csv` | ARIMA actual vs predicted per target per cluster |
| `lstm_*_predictions.csv` | LSTM actual vs predicted per target per cluster |
| `lstm_*_training_history.csv` | Epoch-by-epoch train/val loss per LSTM model |
| `forecast_target_latency.png` | Latency forecast plot |
| `forecast_target_throughput.png` | Throughput forecast plot |

### `verification_output/`
| File | Contents |
|------|----------|
| `full_run_log.txt` | Complete console output from the pipeline run |
| `VERIFICATION_REPORT.md` | This report |

---

## Verification Checklist for Claude AI

Use this checklist to systematically verify the outputs:

- [ ] **Data integrity:** Open `data_summary/clustering_data_describe.csv` — confirm 297 rows, no NaN
- [ ] **Data integrity:** Open `data_summary/forecasting_data_describe.csv` — confirm 5641 rows, no NaN
- [ ] **Filtering:** Open `clustering/zones_filtered.csv` — confirm 257 rows, all `measurement_count >= 50`
- [ ] **K selection:** Open `clustering/k_selection_metrics.csv` — confirm K=2 has highest silhouette
- [ ] **Cluster validity:** Open `clustering/zones_clustered.csv` — compute mean svr1 per cluster, confirm 76.67 and 202.83
- [ ] **Cluster separation:** Open `clustering/per_cluster_silhouette.csv` — confirm < 1% negative silhouette
- [ ] **Temporal split:** Open `forecasting/train_set.csv` and `test_set.csv` — confirm no date overlap
- [ ] **Winsorization caps:** Open `forecasting/winsorization_summary.csv` — confirm caps are 305.94 (latency) and 107.91 (throughput)
- [ ] **Winsorization applied:** Compare `forecasting/train_set_pre_winsorize.csv` max values vs `forecasting/train_set.csv` — confirm target_latency max dropped from ~387.9 to ~305.9
- [ ] **No test leakage:** Confirm caps were computed from train data only (check winsorization_summary.csv cap_value matches train 99th percentile)
- [ ] **Consistent capping:** Confirm all latency-related columns (svr1, target_latency, latency_lag_1h, latency_rolling_3h, latency_rolling_6h) use the same cap value
- [ ] **ARIMA predictions:** Open any `arima_*_predictions.csv` — recompute RMSE from actual/predicted
- [ ] **LSTM predictions:** Open any `lstm_*_predictions.csv` — recompute RMSE from actual/predicted
- [ ] **LSTM training:** Open any `lstm_*_training_history.csv` — confirm loss decreases over epochs
- [ ] **Model comparison:** Open `forecasting/all_forecasting_metrics.csv` — confirm LSTM beats ARIMA on most metrics
- [ ] **Visual check:** View all .png plots for obvious anomalies
