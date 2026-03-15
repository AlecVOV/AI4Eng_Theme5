# 5G Network Performance — Clustering & Forecasting

COS40007 AI for Engineering — Group Design Project

## Project Structure

```
GROUP_PRJ/
├── data/                           # Input datasets
│   ├── clustering_data.csv         # 297 zones, 8 columns
│   ├── forecasting_data.csv        # 5641 hourly records, 29 columns (with lag/rolling features)
│   └── raw/                        # Large raw files (gitignored, not needed)
├── scripts/                        # All training/pipeline scripts
│   ├── preprocess_5g.py            # Raw data → clustering_data.csv + forecasting_data.csv
│   ├── task1_clustering.py         # K-Means + DBSCAN clustering
│   ├── task2_forecasting.py        # ARIMA + LSTM forecasting (V1)
│   ├── run_verification.py         # Full pipeline with detailed logging + winsorization
│   └── run_v2_median_mae.py        # V2: median aggregation + MAE loss
├── outputs/                        # V1 model outputs (plots + CSVs)
├── verification_output/            # Detailed verification artifacts
│   ├── clustering/                 # Cluster metrics, profiles, plots
│   ├── forecasting/                # Predictions, training logs, winsorization summary
│   ├── data_summary/               # Data describe/head CSVs
│   ├── v2_median_mae/              # V2 experiment outputs
│   ├── VERIFICATION_REPORT.md      # Full methodology + checklist
│   └── full_run_log.txt            # Complete console output
├── streamlit_app/                  # Self-contained demo dashboard
│   ├── app.py                      # Streamlit app (4 pages)
│   ├── models/                     # Pre-trained .h5 models (small, ~566KB total)
│   ├── data/                       # App-specific CSVs
│   └── requirements.txt
└── legacy/                         # Old/superseded files (safe to ignore)
```

## Quick Start

### 1. Install dependencies

```bash
pip install pandas numpy scikit-learn statsmodels pmdarima tensorflow matplotlib seaborn streamlit folium plotly
```

### 2. Run the Streamlit demo (no training needed)

The app ships with pre-trained models and data. Just run:

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501` with 4 pages:
- **Cluster Map** — interactive map of zones colored by cluster
- **Cluster Assignment** — input network values, predict which cluster
- **Performance Forecast** — ARIMA vs LSTM predicted vs actual charts
- **Evaluation Metrics** — all plots and metric tables

### 3. Re-run training from scratch (optional)

```bash
# Step 1: Clustering (produces outputs/zones_clustered.csv)
python scripts/task1_clustering.py

# Step 2: Forecasting (needs clustering output first)
python scripts/task2_forecasting.py

# Or run the full verification pipeline (produces everything in verification_output/)
python scripts/run_verification.py
```

## How to Verify the Output

All verification artifacts are in `verification_output/`. Read `verification_output/VERIFICATION_REPORT.md` for the full methodology and verification checklist.

### Quick verification steps

#### Clustering

1. Open `verification_output/clustering/k_selection_metrics.csv`
   - Confirm K=2 has the highest silhouette score (0.2514)

2. Open `verification_output/clustering/zones_clustered.csv`
   - Filter `kmeans_cluster == 0` → mean of `svr1` should be ~76.67 (low latency)
   - Filter `kmeans_cluster == 1` → mean of `svr1` should be ~202.83 (high latency)

3. Open `verification_output/clustering/per_cluster_silhouette.csv`
   - Both clusters should have <1% negative silhouette values

4. View `verification_output/clustering/cluster_maps.png`
   - Clusters should show geographic patterns on the map

#### Forecasting

5. Open `verification_output/forecasting/winsorization_summary.csv`
   - Latency cap should be 305.94 ms (99th percentile of training data)
   - Throughput cap should be 107.91 Mbps
   - Only ~1-3 values clipped per column

6. Open any `verification_output/forecasting/arima_*_predictions.csv`
   - Recompute RMSE: `sqrt(mean((actual - predicted)^2))`
   - Should match the values in `all_forecasting_metrics.csv`

7. Open any `verification_output/forecasting/lstm_*_training_history.csv`
   - Confirm loss decreases over epochs (model is learning)

8. Open `verification_output/forecasting/all_forecasting_metrics.csv`
   - LSTM beats ARIMA on latency (both clusters)
   - Throughput results are mixed (ARIMA wins Cluster 0, LSTM wins Cluster 1)

9. View `verification_output/forecasting/forecast_target_latency.png` and `forecast_target_throughput.png`
   - Predictions should roughly follow the actual values

### Key results summary

| Task | Metric | Value |
|------|--------|-------|
| Clustering | Best K | 2 |
| Clustering | Silhouette Score | 0.2514 |
| Clustering | Cluster 0 | Low Latency / High Throughput (159 zones) |
| Clustering | Cluster 1 | High Latency / Low Throughput (98 zones) |
| Forecasting | Best latency model | LSTM (RMSE=28.43 for Cluster 0) |
| Forecasting | Best throughput model | LSTM (RMSE=5.77 for Cluster 1) |
| Forecasting | Winsorization | 99th percentile capping (latency=305.94, throughput=107.91) |

## Pipeline Overview

```
data/clustering_data.csv
  ├── Filter zones with < 50 measurements
  ├── StandardScaler
  ├── K-Means (K=2) + DBSCAN
  └── Output: cluster labels per zone
        │
        └── Merge into data/forecasting_data.csv
              ├── Pool data per cluster (hourly aggregation)
              ├── Temporal train/test split (train ≤ Jul 18, test ≥ Jul 19)
              ├── Winsorize at 99th percentile (caps from train only)
              ├── ARIMA per cluster
              ├── LSTM per cluster (with lag + rolling features)
              └── Output: next-period latency & throughput predictions

Both outputs → Streamlit dashboard (streamlit_app/)
```
