"""
Task 3: Streamlit UI — 5G Network Performance Dashboard
Cluster Assignment + Performance Forecasting + Interactive Map
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import plotly.express as px
import plotly.graph_objects as go

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")

st.set_page_config(page_title="5G Network Performance Dashboard", layout="wide")
st.title("5G Network Performance — Clustering & Forecasting")

# ── Load saved artifacts ─────────────────────────────────────────────────────
@st.cache_data
def load_data():
    zones = pd.read_csv(os.path.join(OUTPUT_DIR, "zones_clustered.csv"))
    with open(os.path.join(OUTPUT_DIR, "clustering_meta.pkl"), "rb") as f:
        meta = pickle.load(f)
    with open(os.path.join(OUTPUT_DIR, "scaler.pkl"), "rb") as f:
        scaler = pickle.load(f)
    with open(os.path.join(OUTPUT_DIR, "kmeans_model.pkl"), "rb") as f:
        kmeans = pickle.load(f)

    arima_results = {}
    arima_path = os.path.join(OUTPUT_DIR, "arima_results.pkl")
    if os.path.exists(arima_path):
        with open(arima_path, "rb") as f:
            arima_results = pickle.load(f)

    lstm_results = {}
    lstm_path = os.path.join(OUTPUT_DIR, "lstm_results.pkl")
    if os.path.exists(lstm_path):
        with open(lstm_path, "rb") as f:
            lstm_results = pickle.load(f)

    return zones, meta, scaler, kmeans, arima_results, lstm_results

try:
    zones, meta, scaler, kmeans, arima_results, lstm_results = load_data()
except FileNotFoundError as e:
    st.error(f"Missing output files. Please run task1_clustering.py and task2_forecasting.py first.\n\n{e}")
    st.stop()

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Cluster Map", "Cluster Assignment", "Performance Forecast", "Evaluation Metrics"])

cluster_names = meta.get("cluster_names", {})

# ── Page 1: Cluster Map ─────────────────────────────────────────────────────
if page == "Cluster Map":
    st.header("Zone Clusters — Interactive Map")

    zones["cluster_label"] = zones["kmeans_cluster"].map(
        lambda c: f"Cluster {c}: {cluster_names.get(c, '')}"
    )

    fig = px.scatter_mapbox(
        zones, lat="latitude", lon="longitude",
        color="cluster_label",
        hover_data=["square_id", "svr1", "upload_bitrate_mbps", "download_bitrate_mbps", "measurement_count"],
        zoom=10, height=600,
        title="5G Network Zones by Cluster",
        color_discrete_sequence=px.colors.qualitative.Set1
    )
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Cluster Summary")
    summary = zones.groupby("kmeans_cluster").agg(
        num_zones=("square_id", "count"),
        avg_latency=("svr1", "mean"),
        avg_upload=("upload_bitrate_mbps", "mean"),
        avg_download=("download_bitrate_mbps", "mean"),
    ).round(2)
    summary.index = [f"Cluster {c}: {cluster_names.get(c, '')}" for c in summary.index]
    st.dataframe(summary)

# ── Page 2: Cluster Assignment ───────────────────────────────────────────────
elif page == "Cluster Assignment":
    st.header("Cluster Assignment — Predict Zone Group")
    st.write("Enter network performance values to predict which cluster a zone belongs to.")

    col1, col2 = st.columns(2)
    with col1:
        svr1 = st.number_input("Server Latency (ms)", value=100.0, step=1.0)
        upload_bitrate = st.number_input("Upload Bitrate (Mbps)", value=10.0, step=0.5)
        download_bitrate = st.number_input("Download Bitrate (Mbps)", value=18.0, step=0.5)
    with col2:
        latitude = st.number_input("Latitude", value=-37.73, step=0.01, format="%.4f")
        longitude = st.number_input("Longitude", value=144.82, step=0.01, format="%.4f")

    if st.button("Predict Cluster"):
        input_values = np.array([[svr1, upload_bitrate, download_bitrate, latitude, longitude]])
        input_scaled = scaler.transform(input_values)
        prediction = kmeans.predict(input_scaled)[0]

        st.success(f"Predicted Cluster: **{prediction}** — {cluster_names.get(prediction, 'Unknown')}")

        # Show on map
        fig = px.scatter_mapbox(
            zones, lat="latitude", lon="longitude",
            color=zones["kmeans_cluster"].astype(str),
            opacity=0.4, zoom=10, height=500,
            color_discrete_sequence=px.colors.qualitative.Set1
        )
        fig.add_trace(go.Scattermapbox(
            lat=[latitude], lon=[longitude],
            mode="markers",
            marker=dict(size=15, color="black"),
            name="Your Input"
        ))
        fig.update_layout(mapbox_style="open-street-map")
        fig.update_layout(margin={"r": 0, "t": 10, "l": 0, "b": 0})
        st.plotly_chart(fig, use_container_width=True)

# ── Page 3: Performance Forecast ─────────────────────────────────────────────
elif page == "Performance Forecast":
    st.header("Performance Forecast — Predicted vs Actual")

    target = st.selectbox("Target Metric", ["target_latency", "target_throughput"])

    available_clusters = sorted(set(
        [c for (t, c) in arima_results.keys() if t == target] +
        [c for (t, c) in lstm_results.keys() if t == target]
    ))

    if not available_clusters:
        st.warning("No forecasting results available. Run task2_forecasting.py first.")
    else:
        cluster_id = st.selectbox("Select Cluster", available_clusters,
                                  format_func=lambda c: f"Cluster {c}: {cluster_names.get(c, '')}")

        fig = go.Figure()

        if (target, cluster_id) in arima_results:
            r = arima_results[(target, cluster_id)]
            fig.add_trace(go.Scatter(y=r["actual"], mode="lines+markers", name="Actual"))
            fig.add_trace(go.Scatter(y=r["preds"], mode="lines+markers", name=f"ARIMA (RMSE={r['rmse']:.2f})"))

            col1, col2, col3 = st.columns(3)
            col1.metric("ARIMA RMSE", f"{r['rmse']:.2f}")
            col2.metric("ARIMA MAE", f"{r['mae']:.2f}")
            col3.metric("ARIMA MAPE", f"{r['mape']:.1f}%")

        if (target, cluster_id) in lstm_results:
            r = lstm_results[(target, cluster_id)]
            fig.add_trace(go.Scatter(y=r["actual"], mode="lines+markers", name="Actual (LSTM split)", opacity=0.5))
            fig.add_trace(go.Scatter(y=r["preds"], mode="lines+markers", name=f"LSTM (RMSE={r['rmse']:.2f})"))

            col1, col2, col3 = st.columns(3)
            col1.metric("LSTM RMSE", f"{r['rmse']:.2f}")
            col2.metric("LSTM MAE", f"{r['mae']:.2f}")
            col3.metric("LSTM MAPE", f"{r['mape']:.1f}%")

        fig.update_layout(
            title=f"Forecast: {target} — Cluster {cluster_id}",
            xaxis_title="Time Step", yaxis_title=target,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Page 4: Evaluation Metrics ───────────────────────────────────────────────
elif page == "Evaluation Metrics":
    st.header("Model Evaluation Metrics")

    st.subheader("Clustering Metrics (K-Means)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Silhouette Score", f"{meta['silhouette']:.4f}")
    col2.metric("Davies-Bouldin Index", f"{meta['davies_bouldin']:.4f}")
    col3.metric("Calinski-Harabasz Index", f"{meta['calinski_harabasz']:.1f}")

    st.info("Silhouette: higher is better (range -1 to 1). Davies-Bouldin: lower is better. Calinski-Harabasz: higher is better.")

    # Show plots
    for img_name, title in [
        ("elbow_silhouette.png", "Elbow & Silhouette Analysis"),
        ("cluster_maps.png", "Cluster Maps"),
        ("cluster_profiles.png", "Cluster Feature Profiles"),
        ("silhouette_plot.png", "Silhouette Plot"),
    ]:
        img_path = os.path.join(OUTPUT_DIR, img_name)
        if os.path.exists(img_path):
            st.subheader(title)
            st.image(img_path)

    st.subheader("Forecasting Metrics")
    for img_name, title in [
        ("forecast_target_latency.png", "Latency Forecast"),
        ("forecast_target_throughput.png", "Throughput Forecast"),
    ]:
        img_path = os.path.join(OUTPUT_DIR, img_name)
        if os.path.exists(img_path):
            st.subheader(title)
            st.image(img_path)

    # Table of metrics
    if arima_results or lstm_results:
        st.subheader("Forecast Metrics Comparison")
        rows = []
        for (target, cluster_id), r in arima_results.items():
            rows.append({"Target": target, "Cluster": cluster_id, "Model": "ARIMA",
                         "RMSE": r["rmse"], "MAE": r["mae"], "MAPE%": r["mape"]})
        for (target, cluster_id), r in lstm_results.items():
            rows.append({"Target": target, "Cluster": cluster_id, "Model": "LSTM",
                         "RMSE": r["rmse"], "MAE": r["mae"], "MAPE%": r["mape"]})
        if rows:
            metrics_df = pd.DataFrame(rows).round(2)
            st.dataframe(metrics_df, use_container_width=True)
