"""
5G Network Performance Analysis - AI Demonstrator
COS40007 Artificial Intelligence for Engineering
Tabs: Cluster Explorer | Cluster Assignment | Performance Forecast
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import plotly.graph_objects as go

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(APP_DIR, "models")
DATA_DIR = os.path.join(APP_DIR, "data")

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="5G Network Performance Analysis",
    page_icon="📡",
    layout="wide",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("5G Network Analysis")
st.sidebar.markdown("**COS40007** — AI for Engineering")
st.sidebar.markdown("Swinburne University of Technology")
st.sidebar.markdown("---")
st.sidebar.markdown("**Project:** Grouping zones & predicting 5G network performance in Brimbank, Melbourne")

CLUSTER_COLORS = {0: "#1f77b4", 1: "#d62728"}  # Blue, Red
CLUSTER_NAMES = {
    0: "Low Latency / High Throughput",
    1: "High Latency / Low Throughput",
}

# ── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data
def load_zones():
    return pd.read_csv(os.path.join(DATA_DIR, "zones_clustered.csv"))

@st.cache_resource
def load_scaler():
    with open(os.path.join(MODELS_DIR, "scaler.pkl"), "rb") as f:
        return pickle.load(f)

@st.cache_resource
def load_kmeans():
    with open(os.path.join(MODELS_DIR, "kmeans.pkl"), "rb") as f:
        return pickle.load(f)

@st.cache_data
def load_predictions(target, cluster_id, model_type):
    fname = f"{model_type}_{target}_cluster{cluster_id}_predictions.csv"
    path = os.path.join(DATA_DIR, fname)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Cluster Explorer", "Cluster Assignment", "Performance Forecast"])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1: CLUSTER EXPLORER (MAP)
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Cluster Explorer — Zone Map")

    zones = load_zones()

    # Create discrete color column
    zones["cluster_label"] = zones["kmeans_cluster"].map(
        lambda c: f"Cluster {c}: {CLUSTER_NAMES.get(c, '')}"
    )
    color_map = {
        f"Cluster 0: {CLUSTER_NAMES[0]}": CLUSTER_COLORS[0],
        f"Cluster 1: {CLUSTER_NAMES[1]}": CLUSTER_COLORS[1],
    }

    fig = go.Figure()

    for cluster_id in [0, 1]:
        subset = zones[zones["kmeans_cluster"] == cluster_id]
        label = f"Cluster {cluster_id}: {CLUSTER_NAMES[cluster_id]}"
        fig.add_trace(go.Scattermapbox(
            lat=subset["latitude"],
            lon=subset["longitude"],
            mode="markers",
            marker=dict(size=9, color=CLUSTER_COLORS[cluster_id]),
            name=label,
            customdata=np.stack([
                subset["square_id"],
                subset["svr1"].round(1),
                subset["upload_bitrate_mbps"].round(2),
                subset["download_bitrate_mbps"].round(2),
                subset["measurement_count"],
            ], axis=-1),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Latency: %{customdata[1]} ms<br>"
                "Upload: %{customdata[2]} Mbps<br>"
                "Download: %{customdata[3]} Mbps<br>"
                "Measurements: %{customdata[4]}<br>"
                "<extra>" + label + "</extra>"
            ),
        ))

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=-37.75, lon=144.78),
            zoom=10.5,
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=550,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01,
                    bgcolor="rgba(255,255,255,0.85)", font=dict(size=12)),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Cluster summary
    st.subheader("Cluster Profiles")
    col1, col2 = st.columns(2)

    for cluster_id, col in [(0, col1), (1, col2)]:
        subset = zones[zones["kmeans_cluster"] == cluster_id]
        color = CLUSTER_COLORS[cluster_id]
        with col:
            st.markdown(
                f"<div style='border-left: 4px solid {color}; padding-left: 12px;'>"
                f"<h4>Cluster {cluster_id}: {CLUSTER_NAMES[cluster_id]}</h4></div>",
                unsafe_allow_html=True,
            )
            st.metric("Zones", len(subset))
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Latency", f"{subset['svr1'].mean():.1f} ms")
            c2.metric("Avg Upload", f"{subset['upload_bitrate_mbps'].mean():.2f} Mbps")
            c3.metric("Avg Download", f"{subset['download_bitrate_mbps'].mean():.2f} Mbps")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2: CLUSTER ASSIGNMENT
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Cluster Assignment — Predict Zone Group")
    st.write("Enter network performance values to predict which cluster a zone belongs to.")

    col_in1, col_in2 = st.columns(2)
    with col_in1:
        svr1 = st.slider("Latency — svr1 (ms)", 0.0, 500.0, 100.0, 1.0)
        upload = st.slider("Upload Bitrate (Mbps)", 0.0, 50.0, 10.0, 0.5)
        download = st.slider("Download Bitrate (Mbps)", 0.0, 80.0, 20.0, 0.5)
    with col_in2:
        lat = st.slider("Latitude", -37.85, -37.65, -37.75, 0.001, format="%.4f")
        lon = st.slider("Longitude", 144.65, 144.90, 144.78, 0.001, format="%.4f")

    scaler = load_scaler()
    kmeans = load_kmeans()

    input_arr = np.array([[svr1, upload, download, lat, lon]])
    input_scaled = scaler.transform(input_arr)
    prediction = int(kmeans.predict(input_scaled)[0])

    color = CLUSTER_COLORS[prediction]
    name = CLUSTER_NAMES[prediction]

    st.markdown(
        f"<div style='background-color: {color}22; border: 2px solid {color}; "
        f"border-radius: 8px; padding: 16px; margin: 16px 0;'>"
        f"<h3 style='margin:0; color: {color};'>Cluster {prediction}: {name}</h3></div>",
        unsafe_allow_html=True,
    )

    # Comparison table
    st.subheader("How your input compares to cluster averages")
    zones = load_zones()
    cluster_avgs = zones.groupby("kmeans_cluster")[["svr1", "upload_bitrate_mbps", "download_bitrate_mbps"]].mean()

    comp_df = pd.DataFrame({
        "Metric": ["Latency (ms)", "Upload (Mbps)", "Download (Mbps)"],
        "Your Input": [svr1, upload, download],
        f"Cluster 0 Avg": cluster_avgs.loc[0].values.round(2),
        f"Cluster 1 Avg": cluster_avgs.loc[1].values.round(2),
    })
    st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # Small bar chart comparing input to cluster means
    metrics = ["Latency (svr1)", "Upload", "Download"]
    input_vals = [svr1, upload, download]
    c0_vals = cluster_avgs.loc[0].values
    c1_vals = cluster_avgs.loc[1].values

    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(name="Your Input", x=metrics, y=input_vals, marker_color="#2ca02c"))
    fig_comp.add_trace(go.Bar(name="Cluster 0 Avg", x=metrics, y=c0_vals, marker_color=CLUSTER_COLORS[0]))
    fig_comp.add_trace(go.Bar(name="Cluster 1 Avg", x=metrics, y=c1_vals, marker_color=CLUSTER_COLORS[1]))
    fig_comp.update_layout(barmode="group", height=350, margin=dict(t=30))
    st.plotly_chart(fig_comp, use_container_width=True)

    # Show input on map
    st.subheader("Location on map")
    fig_map = go.Figure()
    for cid in [0, 1]:
        subset = zones[zones["kmeans_cluster"] == cid]
        fig_map.add_trace(go.Scattermapbox(
            lat=subset["latitude"], lon=subset["longitude"],
            mode="markers", marker=dict(size=7, color=CLUSTER_COLORS[cid], opacity=0.4),
            name=f"Cluster {cid}", showlegend=True,
        ))
    fig_map.add_trace(go.Scattermapbox(
        lat=[lat], lon=[lon], mode="markers",
        marker=dict(size=14, color="#2ca02c", symbol="circle"),
        name="Your Input",
    ))
    fig_map.update_layout(
        mapbox=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=11),
        margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=400,
    )
    st.plotly_chart(fig_map, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3: PERFORMANCE FORECAST
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("Performance Forecast — LSTM vs ARIMA")

    cluster_sel = st.selectbox(
        "Select Cluster",
        [0, 1],
        format_func=lambda c: f"Cluster {c}: {CLUSTER_NAMES[c]}",
    )

    # Best model config info
    config_info = {
        ("target_latency", 0): "V2 (median + MAE)",
        ("target_latency", 1): "V1 (mean + MSE)",
        ("target_throughput", 0): "V1 (mean + MSE)",
        ("target_throughput", 1): "V2 (median + MAE)",
    }

    for target, target_label in [("target_latency", "Latency (ms)"), ("target_throughput", "Throughput (Mbps)")]:
        st.subheader(f"{target_label} Forecast — Cluster {cluster_sel}")

        config = config_info.get((target, cluster_sel), "")
        st.caption(f"Best model config: {config}")

        lstm_preds = load_predictions(target, cluster_sel, "lstm")
        arima_preds = load_predictions(target, cluster_sel, "arima")

        if lstm_preds is not None:
            fig = go.Figure()

            # Actual values
            fig.add_trace(go.Scatter(
                y=lstm_preds["actual"], mode="lines+markers",
                name="Actual", line=dict(color="#1f77b4", width=2),
                marker=dict(size=5),
            ))

            # LSTM predictions
            rmse_lstm = np.sqrt(np.mean((lstm_preds["actual"] - lstm_preds["predicted"])**2))
            nonzero = lstm_preds["actual"] != 0
            mape_lstm = np.mean(np.abs(
                (lstm_preds.loc[nonzero, "actual"] - lstm_preds.loc[nonzero, "predicted"])
                / lstm_preds.loc[nonzero, "actual"]
            )) * 100 if nonzero.any() else float("nan")

            fig.add_trace(go.Scatter(
                y=lstm_preds["predicted"], mode="lines+markers",
                name=f"LSTM (RMSE={rmse_lstm:.2f}, MAPE={mape_lstm:.1f}%)",
                line=dict(color="#2ca02c", width=2, dash="dash"),
                marker=dict(size=5, symbol="triangle-up"),
            ))

            # ARIMA predictions (flat-line comparison)
            if arima_preds is not None:
                rmse_arima = np.sqrt(np.mean((arima_preds["actual"] - arima_preds["predicted"])**2))
                # Extend ARIMA to match LSTM length for visual comparison
                arima_line = arima_preds["predicted"].values
                if len(arima_line) > len(lstm_preds):
                    arima_line = arima_line[:len(lstm_preds)]
                elif len(arima_line) < len(lstm_preds):
                    # pad with last value
                    arima_line = np.concatenate([arima_line, np.full(len(lstm_preds) - len(arima_line), arima_line[-1])])

                fig.add_trace(go.Scatter(
                    y=arima_line[:len(lstm_preds)], mode="lines",
                    name=f"ARIMA (RMSE={rmse_arima:.2f})",
                    line=dict(color="#d62728", width=1.5, dash="dot"),
                ))

            fig.update_layout(
                xaxis_title="Time Step", yaxis_title=target_label,
                height=400, margin=dict(t=30),
                legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Metrics row
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("LSTM RMSE", f"{rmse_lstm:.2f}")
            mc2.metric("LSTM MAPE", f"{mape_lstm:.1f}%")
            if arima_preds is not None:
                mc3.metric("ARIMA RMSE", f"{rmse_arima:.2f}")
        else:
            st.warning(f"No prediction data found for {target} Cluster {cluster_sel}")

    st.markdown("---")
    st.caption("Models trained on 5G network data from Brimbank, Melbourne (July 2022). "
               "ARIMA serves as a statistical baseline; LSTM captures temporal patterns via lag and rolling features.")
